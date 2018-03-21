import base64
import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is np.ndarray:
            data = obj.tobytes()
            data_b64 = base64.b64encode(data).decode('ascii')
            return {
                "__ndarray__": data_b64,
                "dtype":  str(obj.dtype),
                "shape": list(obj.shape)
            }

        return super().default(obj)


def json_numpy_obj_hook(dct):
    if isinstance(dct, dict) and '__ndarray__' in dct:
        data = base64.b64decode(dct['__ndarray__'])
        dtype = dct['dtype']
        shape = dct['shape']
        return np.frombuffer(data, dtype).reshape(shape)

    return dct


