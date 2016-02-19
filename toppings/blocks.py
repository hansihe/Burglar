from . import Topping
import jawa

class BlocksTopping(Topping):
    @staticmethod
    def act(ctx):
        blocks_class_mapping = ctx.mapping.resolve_class("net/minecraft/block/Block")
        blocks_class = ctx.jar.cls(blocks_class_mapping)

        register_blocks_mapping = ctx.mapping.resolve_method(
                blocks_class_mapping, "registerBlocks")
        register_blocks_sig = register_blocks_mapping.find_signature()
        register_blocks_method = blocks_class.methods.find_one(**register_blocks_sig)

        # More or less bootlegged from Burger
        blocks = []
        stack = []
        current_block = dict(calls=list())
        for ins in register_blocks_method.code.disassemble():
            name = ins.mnemonic

            if name == "new":
                const_i = ins.operands[0][1]
                const = blocks_class.constants[const_i]
                block_class = ctx.mapping.resolve_class_obf(const.name.value)
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

                cls = ctx.mapping.resolve_class_obf(const.class_.name.value)
                method_mapping = ctx.utils.resolve_method_parents(cls, const.name_and_type.name.value, const.name_and_type.descriptor.value, name_obfuscated=True)

                # End of block regs
                if method_mapping and method_mapping.deobf_id == "validateKey":
                    break

                current_block["calls"].append((const, method_mapping, stack))
                stack = []

            elif name == "invokestatic":
                const_i = ins.operands[0][1]
                const = blocks_class.constants[const_i]

                method_mapping = ctx.mapping.resolve_const_method_ref(const)
                #print(method_mapping)

                if method_mapping.deobf_id != "registerBlock":
                    raise Exception("Update needed")

                blocks.append(current_block)
                current_block = None
                stack = []
            elif name == "getstatic":
                const_i = ins.operands[0][1]
                const = blocks_class.constants[const_i]
                field = ctx.mapping.resolve_const_field_ref(const)
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
