import numpy as np
## sensor

class Station:
    """
    name:     num_id (e.g. "109GAN")
    location: ["lat", "long"]
    """

    def __init__(self, name, location):
        self.name = name
        self.location = location

class Sensor(Station):
    """
    Station: Station object,
    rate   : sampling rate,
    height : switch height,
    offset : offset of the switch,
    type   : sensor type,
    date   : the initial date/time,
    data   : sea level measurements
    """

    def __init__(self, Station, rate, height,typ,date0, data, info, header):
        # Station.__init__(self, Station.name, Station.location)
        self.name = Station.name
        self.location = Station.location
        self.rate = rate
        self.height = height
        self.type = typ
        self.date = date0
        self.data = data
        self.time_info = info
        self.header = header


    def get_flat_data(self):
        return self.data.flatten()

    def get_time_vector(self):
        return np.array([self.date + np.timedelta64(i*int(self.rate),'m') for i in range(self.get_flat_data().size)])
