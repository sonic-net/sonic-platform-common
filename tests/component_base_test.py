from sonic_platform_base.component_base import ComponentBase

class TestComponentBase:

    def test_get_firmware_update_notification(self):
        cpnt = ComponentBase()
        assert(cpnt.get_firmware_update_notification(None) == "None")
