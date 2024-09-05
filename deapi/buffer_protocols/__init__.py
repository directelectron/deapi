# Choose the right protocol buffer version based on the python version

import sys

pyVersion = sys.version.split("(")[0][0:4].split(".")


if int(pyVersion[0]) < 3:
    from cStringIO import (
        StringIO,
    )  # use string io to speed up, refer to http://www.skymind.com/~ocrow/python_string/
    import deapi.buffer_protocols.pb_2_3_0 as pb
else:
    from io import (
        StringIO,
    )  # use string io to speed up, refer to http://www.skymind.com/~ocrow/python_string/

    long = int  # python 3 no longer has int
    if int(pyVersion[1]) >= 10:
        # import pb_3_19_3 as pb
        import deapi.buffer_protocols.pb_3_23_3 as pb
    elif int(pyVersion[1]) >= 8:
        import deapi.buffer_protocols.pb_3_11_4 as pb
    else:
        import deapi.buffer_protocols.pb_3_6_1 as pb

__all__ = [
    "pb",
]
