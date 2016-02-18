from srg_file import Mapping
from bytecode_parser import SimpleDecompiler
import jawa
import zipfile
import StringIO

class McJar(object):
    def __init__(self, path, mapping):
        self.class_cache = {}
        self.path = path
        self.jar = zipfile.ZipFile(path)
        self.mapping = mapping

    def cls(self, class_mapping):
        if self.class_cache.get(class_mapping):
            return self.class_cache[class_mapping]

        name = class_mapping.obf_name + ".class"
        class_file = jawa.ClassFile(StringIO.StringIO(self.jar.read(name)))
        self.class_cache[class_mapping] = class_file

        return class_file

class McJarUtils(object):
    def __init__(self, mc_jar, mapping):
        self.jar = mc_jar
        self.mapping = mapping

    def resolve_method_parents(self, class_mapping, name, signature=None, name_obfuscated=False):
        cls = class_mapping
        jar_class = None
        method = None
        while method == None:
            jar_class = self.jar.cls(cls)
            method = self.mapping.resolve_method(cls, name, signature, name_obfuscated)
            try:
                cls = mapping.resolve_class_obf(jar_class.super_.name.value)
            except KeyError as e:
                break
        return method

mapping = Mapping("temp/")
jar = McJar("temp/mc.jar", mapping)
jar_utils = McJarUtils(jar, mapping)
simple_decompiler = SimpleDecompiler(jar_utils)

blocks_class_mapping = mapping.resolve_class("net/minecraft/block/Block")
blocks_class = jar.cls(blocks_class_mapping)

register_blocks_mapping = mapping.resolve_method(blocks_class_mapping, "registerBlocks")
register_blocks_sig = register_blocks_mapping.find_signature()
register_blocks_method = blocks_class.methods.find_one(**register_blocks_sig)

simple_decompiler.decomp_method(register_blocks_mapping)

# More or less bootlegged from Burger
blocks = []
stack = []
current_block = dict(calls=list())
for ins in register_blocks_method.code.disassemble():
    name = ins.mnemonic
    
    if name == "new":
        const_i = ins.operands[0][1]
        const = blocks_class.constants[const_i]
        block_class = mapping.resolve_class_obf(const.name.value)
        current_block = dict(cls=block_class, calls=list())

        if len(stack) == 2:
            current_block["numeric_id"] = stack[0]
            current_block["text_id"] = stack[1]
        elif len(stack) == 1:
            current_block["numeric_id"] = stack[0]
            current_block["text_id"] = "air"
        stack = []
    elif name.startswith("iconst"):
        stack.append(int(ins.mnemonic[-1]))
    elif name.startswith("fconst"):
        stack.append(float(ins.mnemonic[-1]))
    elif name.endswith("ipush"):
        stack.append(ins.operands[0][1])
    elif name in ("ldc", "ldc_w"):
        const_i = ins.operands[0][1]
        const = blocks_class.constants[const_i]

        if const.TAG == jawa.constants.ConstantString.TAG:
            stack.append(const.string.value)
        else:
            stack.append(const.value)
    elif name in ("invokevirtual", "invokespecial"):
        const_i = ins.operands[0].value
        const = blocks_class.constants[const_i]

        cls = mapping.resolve_class_obf(const.class_.name.value)
        method_mapping = jar_utils.resolve_method_parents(cls, const.name_and_type.name.value, const.name_and_type.descriptor.value, name_obfuscated=True)

        # End of block regs
        if method_mapping and method_mapping.deobf_id == "validateKey":
            break

        current_block["calls"].append((const, method_mapping, stack))
        stack = []

    elif name == "invokestatic":
        const_i = ins.operands[0][1]
        const = blocks_class.constants[const_i]
    
        method_mapping = mapping.resolve_const_method_ref(const)
        #print(method_mapping)

        if method_mapping.deobf_id != "registerBlock":
            raise Exception("Update needed")

        blocks.append(current_block)
        current_block = None
        stack = []
    elif name == "getstatic":
        const_i = ins.operands[0][1]
        const = blocks_class.constants[const_i]
        field = mapping.resolve_const_field_ref(const)
        assert(field != None)
        stack.append(field)
    else:
        pass
        #print(ins)

def process_block(block):
    for call in block["calls"]:
        print(call)

import pprint
#pprint.pprint(map(process_block, blocks))
