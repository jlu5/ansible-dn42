def zfill(s, width):
    return str(s).zfill(width)

class FilterModule():
    def filters(self):
        return {
            'zfill': zfill
        }
