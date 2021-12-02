from ..xcvr_field import NumberRegField
from ..xcvr_field import RegField
from .. import consts
from ...codes.public.sff8024 import Sff8024

class CableLenField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.LEN_MULT_FIELD]
        super(CableLenField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        base_len = super(CableLenField, self).decode(raw_data, **decoded_deps)
        len_mult = decoded_deps.get(consts.LEN_MULT_FIELD)
        mult = 10 ** (len_mult - 1)
        return base_len * mult

class ApplicationAdvertField(RegField):
    """
    Interprets application advertising bytes as a string
    """
    def __init__(self, name, offset, *fields, **kwargs):
        super(ApplicationAdvertField, self).__init__(name, offset, *fields, **kwargs)
        self.size = kwargs.get("size")

    def decode(self, raw_data, **decoded_deps):
        media_dict = {
            1: Sff8024.NM_850_MEDIA_INTERFACE,
            2: Sff8024.SM_MEDIA_INTERFACE,
            3: Sff8024.PASSIVE_COPPER_MEDIA_INTERFACE,
            4: Sff8024.ACTIVE_CABLE_MEDIA_INTERFACE,
            5: Sff8024.BASE_T_MEDIA_INTERFACE
        }

        # Select the media dictionary based on media type(i.e. BYTE 85)
        media_if_dict = media_dict.get(raw_data[0])
        host_if_dict = Sff8024.HOST_ELECTRICAL_INTERFACE

        if media_if_dict is None:
            return None

        idx = 1
        pos = 1
        dat = {}
        while pos < self.size:
            appl = { }

            code = raw_data[pos+0]
            if code in [0x00, 0xff]:
                break
            if code in host_if_dict:
                appl['host_electrical_interface_id'] = host_if_dict[code]
            else:
                appl['host_electrical_interface_id'] = 'Unknown'

            code = raw_data[pos+1]
            if code in [0x00, 0xff]:
                break
            if code in media_if_dict:
                appl['module_media_interface_id'] = media_if_dict[code]
            else:
                appl['module_media_interface_id'] = 'Unknown'

            appl['host_lane_count'] = raw_data[pos+2] >> 4
            appl['media_lane_count'] = raw_data[pos+2] & 0xf
            appl['host_lane_assignment_options'] = raw_data[pos+3]
            appl['media_lane_assignment_options'] = None

            dat[idx] = appl
            idx += 1
            pos += 4

        return str(dat)
