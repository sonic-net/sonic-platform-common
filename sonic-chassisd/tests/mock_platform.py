class MockDevice:
    def __init__(self):
        self.name = None
        self.presence = True
        self.model = 'Module Model'
        self.serial = 'Module Serial'

    def get_name(self):
        return self.name

    def get_presence(self):
        return self.presence

    def get_model(self):
        return self.model

    def get_serial(self):
        return self.serial


class MockModule(MockDevice):
    def __init__(self, module_index, module_name, module_desc, module_type, module_slot,
                 module_serial, asic_list=[]):
        self.module_index = module_index
        self.module_name = module_name
        self.module_desc = module_desc
        self.module_type = module_type
        self.hw_slot = module_slot
        self.module_status = ''
        self.admin_state = 1
        self.supervisor_slot = 16
        self.midplane_access = False
        self.asic_list = asic_list
        self.module_serial = module_serial
 
    def get_name(self):
        return self.module_name

    def get_description(self):
        return self.module_desc

    def get_type(self):
        return self.module_type

    def get_slot(self):
        return self.hw_slot

    def get_oper_status(self):
        return self.module_status

    def set_oper_status(self, status):
        self.module_status = status

    def set_admin_state(self, up):
        self.admin_state = up

    def get_admin_state(self):
        return self.admin_state

    def get_midplane_ip(self):
        return self.midplane_ip

    def set_midplane_ip(self):
        if self.supervisor_slot == self.get_slot():
            self.midplane_ip = '192.168.1.100'
        else:
            self.midplane_ip = '192.168.1.{}'.format(self.get_slot())

    def is_midplane_reachable(self):
        return self.midplane_access

    def set_midplane_reachable(self, up):
        self.midplane_access = up

    def get_all_asics(self):
        return self.asic_list

    def get_serial(self):
        return self.module_serial

class MockChassis:
    def __init__(self):
        self.module_list = []
        self.midplane_supervisor_access = False

    def get_num_modules(self):
        return len(self.module_list)

    def get_module(self, index):
        module = self.module_list[index]
        return module

    def get_all_modules(self):
        return self.module_list

    def get_module_index(self, module_name):
        for module in self.module_list:
            if module.module_name == module_name:
                return module.module_index
        return -1

    def init_midplane_switch(self):
        return True

    def get_serial(self):
        return "Serial No"

    def get_model(self):
        return "Model A"

    def get_revision(self):
        return "Rev C"
