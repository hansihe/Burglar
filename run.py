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

class Context(object):
    def __init__(self, mapping, jar, utils, decomp):
        self.mapping = mapping
        self.jar = jar
        self.utils = utils
        self.decomp = decomp

mapping = Mapping("temp/")
jar = McJar("temp/mc.jar", mapping)
jar_utils = McJarUtils(jar, mapping)
simple_decompiler = SimpleDecompiler(jar_utils)
ctx = Context(mapping, jar, jar_utils, simple_decompiler)

from toppings.blocks import BlocksTopping
BlocksTopping.act(ctx)
