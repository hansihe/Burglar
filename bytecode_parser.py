class SimpleDecompiler(object):
    def __init__(self, jar_utils):
        self.jar_utils = jar_utils
        self.jar = jar_utils.jar
        self.mapping = jar_utils.mapping

    def decomp_method(self, method_mapping):
        jar_class = self.jar.cls(method_mapping.class_mapping)
        jar_method = jar_class.methods.find_one(**method_mapping.find_signature())

        self.actions = []
        self.stack = []
        self.method_mapping = method_mapping
        self.jar_class = jar_class
        self.jar_method = jar_method

        self.visiting_new = False
        
        for ins in jar_method.code.disassemble():
            self.visit_instruction(ins)

    def visit_instruction(self, ins):
        mne = ins.mnemonic

        if mne.endswith("ipush"): # Pushing constants
            self.stack.append(ins.operands[0].value)
        elif mne in ("ldc", "ldc_w", "ldc2_w"):
            const = self.jar_class.constants[ins.operands[0].value]
            self.stack.append(const)
        elif mne == "aconst_null":
            self.stack.append(None)
        elif mne == "iconst_m1":
            self.stack.append(-1)
        elif mne.startswith("iconst_"):
            self.stack.append(int(mne[-1]))
        elif mne.startswith("lconst_"):
            self.stack.append(int(mne[-1]))
        elif mne.startswith("fconst_"):
            self.stack.append(float(mne[-1]))
        elif mne.startswith("dconst_"):
            self.stack.append(float(mne[-1]))
        elif mne == "nop": # Stack manipulation
            pass
        elif mne == "pop":
            self.stack.pop()
        elif mne == "pop2":
            self.stack.pop()
            self.stack.pop()
        elif mne == "dup":
            self.stack.append(self.stack[-1])
        elif mne == "getstatic":
            const = self.jar_class.constants[ins.operands[0].value]
            cls = self.mapping.resolve_class_obf(const.class_.name.value)
            method = self.mapping.resolve_field(cls, 
                    const.name_and_type.name.value, name_obfuscated=True)
            self.stack.append(method)
        elif mne == "new":
            const = self.jar_class.constants[ins.operands[0].value]
            cls = self.mapping.resolve_class_obf(const.name.value)
            self.visiting_new = cls
        elif mne in ("invokevirtual", "invokespecial"): # Invocation
            const = self.jar_class.constants[ins.operands[0].value]

            try:
                cls = self.mapping.resolve_class_obf(const.class_.name.value)
            except KeyError as e:
                # The class is not in the jar, call to external lib TODO
                self.stack.append(const)
                return

            nt = const.name_and_type
            if nt.name.value == "<init>":
                #constructor, TODO
                if not self.visiting_new:
                    raise Exception("Init outside of constructor invocation")
                if self.visiting_new != cls:
                    raise Exception("Class instance does not match constructor invocation class")
                self.actions.append((cls, nt.descriptor.value, self.stack))
                self.visiting_new = False
            else:
                self.stack.append(self.jar_utils.resolve_method_parents(cls, 
                        nt.name.value, nt.descriptor.value, name_obfuscated=True))
        elif mne == "invokestatic":
            const = self.jar_class.constants[ins.operands[0].value]
            nt = const.name_and_type
            cls = self.mapping.resolve_class_obf(const.class_.name.value)
            method = self.jar_utils.resolve_method_parents(cls, 
                    nt.name.value, nt.descriptor.value, name_obfuscated=True)
            self.actions.append(method)
        else:
            pass
            print(("Unknown ins", ins))
