import re
import csv
from collections import defaultdict
from jawa.util.descriptor import method_descriptor
import jawa

pk_regex = re.compile("^PK: (\S+) (\S+)$")
cl_regex = re.compile("^CL: (\S+) (\S+)$")
fd_regex = re.compile("^FD: (\S+) (\S+)$")
md_regex = re.compile("^MD: (\S+) (\S+) (\S+) (\S+)$")

def method_path_get_id(path):
    split = path.split("/")
    return ('/'.join(split[0:-1]), split[-1])

def parse_srg_line(line):
    if line.startswith("PK"): # package
        s = pk_regex.search(line)
        return ("PK", (s.group(1), s.group(2)))
    elif line.startswith("CL"): # class
        s = cl_regex.search(line)
        return ("CL", (s.group(1), s.group(2)))
    elif line.startswith("FD"): # field
        s = fd_regex.search(line)
        return ("FD", (s.group(1), s.group(2)))
    elif line.startswith("MD"): # method
        s = md_regex.search(line)
        return ("MD", (
                (s.group(1), method_descriptor(s.group(2))), 
                (s.group(3), method_descriptor(s.group(4)))))
    else:
        raise RuntimeError("Unknown field in srg file: %s" % line)

def parse_srg_file(path):
    packages = []
    classes = []
    fields = []
    methods = []

    with open(path, "r") as srg_file:
        for entry in srg_file:
            parsed = parse_srg_line(entry)
            if parsed[0] == "PK":
                packages.append(parsed[1])
            elif parsed[0] == "CL":
                classes.append(parsed[1])
            elif parsed[0] == "FD":
                fields.append(parsed[1])
            elif parsed[0] == "MD":
                methods.append(parsed[1])

    return dict(packages=packages, classes=classes,
            fields=fields, methods=methods)

class MappingError(Exception):
    pass

srg_func_re = re.compile("^func_\d+_[a-zA-Z]+$")

class ClassMapping(object):
    def __init__(self, srg_entry):
        self.obf_name = srg_entry[0]
        self.searge_name = srg_entry[1]

    def __str__(self):
        return "ClassMapping(%s, %s)" % (self.searge_name, self.obf_name)
    def __repr__(self):
        return str(self)

class MethodMapping(object):

    @classmethod
    def new(cls, srg_entry, mapping, method_mappings, param_mappings):
        (path, srg_id) = method_path_get_id(srg_entry[1][0])

        param_mapping = None
        if srg_func_re.match(srg_id):
            param_mapping = param_mappings.get(srg_id.split("_")[1])

        class_mapping = mapping.resolve_class(path)

        return cls(srg_entry, class_mapping, method_mappings.get(srg_id), param_mapping)

    def __init__(self, srg_entry, class_mapping, method_mapping, param_mapping):
        (path, srg_id) = method_path_get_id(srg_entry[1][0])

        self.params = param_mapping
        self.class_mapping = class_mapping

        self.obf_id = method_path_get_id(srg_entry[0][0])[1]
        self.obf_name = srg_entry[0][0]
        self.obf_type = srg_entry[0][1]
        self.searge_id = srg_id
        self.searge_name = srg_entry[1][0]
        self.searge_type = srg_entry[1][1]
        if method_mapping:
            self.deobf_id = method_mapping[1]
            self.deobf_name = path + "/" + method_mapping[1]
            #self.side = method_mapping[2]
            self.comment = method_mapping[3]
        else:
            self.deobf_id = self.searge_id
            self.deobf_name = self.searge_name
            self.comment = ""

    def __str__(self):
        return "MethodMapping(%s, %s, %s)" % (self.deobf_id, self.obf_id, self.class_mapping)
    def __repr__(self):
        return str(self)

    def find_signature(self):
        return dict(
                name=self.obf_id, 
                args=self.obf_type.args_descriptor, 
                returns=self.obf_type.returns_descriptor)

class FieldMapping(object):
    @classmethod
    def new(cls, srg_entry, mapping, field_ids):
        (path, srg_id) = method_path_get_id(srg_entry[1])
        class_mapping = mapping.resolve_class(path)

        field_mapping_data = field_ids.get(srg_id)

        return cls(srg_entry, class_mapping, field_mapping_data)

    def __init__(self, srg_entry, class_mapping, field_mapping):

        self.class_mapping = class_mapping

        self.obf_id = method_path_get_id(srg_entry[0])[1]
        self.obf_name = srg_entry[0]

        self.searge_id = method_path_get_id(srg_entry[1])[1]
        self.searge_name = srg_entry[1]
        if field_mapping:
            self.deobf_id = field_mapping[1]
            #self.side = field_mapping[2]
            self.comment = field_mapping[3]
        else:
            self.deobf_id = self.searge_id
            self.comment = ""

    def __str__(self):
        return "FieldMapping(%s, %s, %s)" % (self.deobf_id, self.obf_id, self.class_mapping)
    def __repr__(self):
        return str(self)

class Mapping(object):
    def __init__(self, path):
        self.srg = parse_srg_file(path + "joined.srg")

        # Classes
        self.classes = []
        for cls in self.srg["classes"]:
            self.classes.append(ClassMapping(cls))
        # Indexes to make data access quicker
        self.srg_name_classes = dict(map(lambda c: (c.searge_name, c), self.classes))
        self.obf_name_classes = dict(map(lambda c: (c.obf_name, c), self.classes))

        # Methods
        # Method name mappings
        method_names = dict()
        with open(path + "methods.csv", "r") as methods_csv:
            methods = csv.reader(methods_csv)
            header = next(methods)
            for entry in methods:
                method_names[entry[0]] = entry

        # Method parameter mappings
        param_ids = dict()
        with open(path + "params.csv", "r") as params_csv:
            params = csv.reader(params_csv)
            header = next(params)
            for entry in params:
                param_id = entry[0].split("_")[1]
                if not param_ids.get(param_id):
                    param_ids[param_id] = list()
                param_ids[param_id].append(entry)

        # Assemble the MethodMappings from the data we parsed
        self.methods = []
        self.class_mapping_methods = defaultdict(lambda: list())
        for method in self.srg["methods"]:
            mapping = MethodMapping.new(method, self, method_names, param_ids)
            self.class_mapping_methods[mapping.class_mapping].append(mapping)
            self.methods.append(mapping)

        field_ids = dict()
        with open(path + "fields.csv", "r") as fields_csv:
            fields = csv.reader(fields_csv)
            header = next(fields)
            for entry in fields:
                field_ids[entry[0]] = entry

        self.fields = []
        self.class_mapping_fields = defaultdict(lambda: list())
        for field in self.srg["fields"]:
            mapping = FieldMapping.new(field, self, field_ids)
            self.class_mapping_fields[mapping.class_mapping].append(mapping)
            self.fields.append(mapping)

    # Resolves a ClassMapping from a deobfuscated class name
    def resolve_class(self, path):
        return self.srg_name_classes[path]
    # Resolves a ClassMapping from a obfuscated class name
    def resolve_class_obf(self, path):
        return self.obf_name_classes[path]

    # Returns all MethodMappings for a given class mapping
    def class_methods(self, class_mapping):
        return self.class_mapping_methods[class_mapping]
    def class_fields(self, class_mapping):
        return self.class_mapping_fields[class_mapping]

    def resolve_const_method_ref(self, const, class_mapping=None):
        if const.TAG == jawa.constants.ConstantMethodRef.TAG:
            cls = class_mapping or self.resolve_class_obf(const.class_.name.value)
            return self.resolve_method(cls, const.name_and_type.name.value, const.name_and_type.descriptor.value, name_obfuscated=True)
    def resolve_const_field_ref(self, const, class_mapping=None):
        if const.TAG == jawa.constants.ConstantFieldRef.TAG:
            cls = class_mapping or self.resolve_class_obf(const.class_.name.value)
            return self.resolve_field(cls, const.name_and_type.name.value, name_obfuscated=True)

    # Resolves a MethodMapping given a class mapping and a method name
    def resolve_method(self, class_mapping, name, signature=None, name_obfuscated=False):
        class_methods = self.class_methods(class_mapping)
        for method in class_methods:
            if name_obfuscated:
                if signature and method.obf_type.descriptor != signature:
                    continue
                if method.obf_id == name:
                    return method
            else:
                if signature and method.searge_type.descriptor != signature:
                    continue
                if method.deobf_id == name:
                    return method
    # TODO: This might not work as we are not able to look at signatures
    def resolve_field(self, class_mapping, name, name_obfuscated=False):
        class_fields = self.class_fields(class_mapping)
        for field in class_fields:
            if name_obfuscated:
                if field.obf_id == name:
                    return field
            else:
                if field.deobf_id == name:
                    return field
