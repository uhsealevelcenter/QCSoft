# interactive_plot
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path

class PointBrowser:
    """
    Click on a point to select and highlight it -- the data that
    generated the point will be shown in the lower axes.  Use the 'n'
    and 'b' keys to browse through the next and previous points
    """

    np = __import__('numpy')

    def __init__(self, xs, ys, ax, line, fig, outl):

        print("INIT")
        self.fig = fig
        self.xs = xs
        self.ys = ys
        self.ax = ax
        self.line = line
        self.outl_ind = 0
        self.pan_index = -1
        self.jump_step = 600
        self.outl = outl[0]
        self.deleted = []
        self.bulk_deleted = []
        self.onDataEnd = EventHook()
        # print("self.outl", self.outl)
        if self.outl.any():
            self.lastind = self.outl[self.outl_ind]
            # print("self.outl_ind", self.outl_ind)
        else:
            self.lastind = 0
        self.text = self.ax.text(0.7, 0.95, 'selected: none', bbox=dict(facecolor='red', alpha=0.5),
                                 transform=self.ax.transAxes, va='top')
        self.selected, = self.ax.plot([self.xs[self.lastind]], [self.ys[self.lastind]], 'o', ms=12, alpha=0.4,
                                      color='red', visible=True)

        # pts = self.ax.scatter(self.xs, self.ys, s=30, facecolors='none')
        self.collection = self.ax.scatter(self.xs, self.ys, s=30, facecolors='none')
        self.xys = self.collection.get_offsets()
        self.lasso = LassoSelector(self.ax, onselect=self.onselect, button=3)

    def onpress(self, event):
        # print("ON PRESS")
        if self.lastind is None:
            return
        jump_step = 600
        # undo deletions made
        if event.key == 'ctrl+z' and self.deleted:
            # print("UNDO DELETIONS")
            index, data = self.deleted.pop().popitem()
            self.xs[index] = data[0]
            self.ys[index] = data[1]
            # update UNDONE marker index
            self.lastind = index
            self.update(event = event)
        if event.key == 'ctrl+b' and self.bulk_deleted:
            for data in self.bulk_deleted:
                for key,value in data.items():
                    self.xs[key] = value[0]
                    self.ys[key] = value[1]
            self.bulk_deleted = []
            # update UNDONE marker index
            # self.lastind = index
            self.on_bulk_delete()
            self.show_home_view()
            # return
        if event.key not in ('n', 'b', 'd', 'right', 'left', '0', 'ctrl+z', 'ctrl+b'):
            return
        if event.key == '0':
            self.show_home_view()
        if event.key == 'right' or event.key == 'left':
            if event.key == 'right':
                self.pan_index = self.pan_index + 1
            else:
                self.pan_index = self.pan_index - 1

            self.onpan(self.pan_index)

        if event.key == 'd':
            # print('Delete')
            self.ondelete(self.lastind)
            self.ys[self.lastind] = 9999
            if (self.lastind in self.outl):
                self.outl_ind = self.next_pointer(self.ys, self.outl, self.outl_ind, +1)
                # # skip over deleted values in outliers
                # while self.ys[self.outl[self.outl_ind]]==9999:
                #     self.outl_ind += 1
                #     if self.outl_ind > len(self.outl)-1:
                #         break
        if (self.lastind in self.outl):
            if event.key == 'n':
                self.outl_ind = self.next_pointer(self.ys, self.outl, self.outl_ind, +1)
            if event.key == 'b':
                self.outl_ind = self.next_pointer(self.ys, self.outl, self.outl_ind, -1)
            self.outl_ind = self.np.clip(self.outl_ind, 0, len(self.outl) - 1)
            self.lastind = self.outl[self.outl_ind]
        else:
            if event.key == 'n' or event.key == 'd':
                self.lastind = self.next_pointer_all(self.ys, self.lastind, +1)
                # while self.ys[self.lastind]==9999:
                #     self.lastind += 1
                #     if self.lastind > len(self.ys)-1:
                #         break
            if event.key == 'b':
                self.lastind = self.next_pointer_all(self.ys, self.lastind, -1)

        # if(self.outl_ind>-1):
        # if(self.lastind in self.outl):
        #     self.lastind = self.outl[self.outl_ind]
        # else:
        #     if  event.key == 'n' or event.key == 'd':
        #         self.lastind += 1
        #     if event.key == 'b':
        #         self.lastind -= 1
        # else:
        #     self.lastind = 0

        self.lastind = self.np.clip(self.lastind, 0, len(self.xs) - 1)

        # if event.key != '0':
        #     self.pan_index = self.lastind // self.jump_step
        #     self.onpan(self.pan_index)

        # print("NK ", self.lastind, self.outl)
        # print("outl_indl ", self.outl_ind)
        # self.lastind = self.np.clip(self.lastind, 0, len(self.xs) - 1)
        self.update(event = event)

    def onpick(self, event):
        # print("ON PICK CALLED")
        # print(event.artist)
        if event.artist != self.line or event.mouseevent.button != 1:
            return True

        N = len(event.ind)
        if not N:
            return True

        # the click locations
        x = event.mouseevent.xdata
        y = event.mouseevent.ydata
        #
        #         print("y", y)
        #         print("event.ind", event.ind)
        #         print("self.ys[event.ind]", self.ys[event.ind])
        #         print("x", x)
        # print("self.xs[event.ind]", self.xs[event.ind])
        distances = self.np.hypot(x - event.ind, y - self.ys[event.ind])
        # print("distances", distances)
        indmin = distances.argmin()
        dataind = event.ind[indmin]
        # this_artist = event.artist #the picked object is available as event.artist
        # print(this_artist) #For debug just to show you which object is picked
        # plt.gca().picked_object = this_artist

        # On mouse click pan and zoom to the clicked section
        self.pan_index = dataind // self.jump_step
        self.onpan(self.pan_index)

        self.lastind = dataind
        self.update(event = None)

    def update(self, event = None):
        # print("UPDATE IS CALLED")
        if self.lastind is None:
            return

        dataind = self.lastind

        # index of an outlier needs to be updated
        if (dataind in self.outl):
            self.outl_ind = self.np.argwhere(self.outl == dataind)[0][0]

        # print("UPDATED OUTLIER INDEX", self.outl_ind)
        # pan the view to the highlighted point
        if event:
            if(event.key != '0' and event.key != 'left' and event.key != 'right'):
                self.pan_index = self.lastind // self.jump_step
                self.onpan(self.pan_index)
        # print("outlier index", self.outl_ind)
        # print("LAST index", self.lastind)
        self.selected.set_visible(True)
        self.selected.set_data(self.xs[dataind], self.ys[dataind])
        # self.text.set_text('selected: %d' % dataind + 'Value: %d' % self.ys[dataind] )
        self.text.set_text(
            'selected date: %s' % self.np.datetime_as_string(self.xs[dataind], unit='m') + ' Value: %s' % self.ys[
                dataind])
        nines_ind = self.np.where(self.ys == 9999)
        nonines_data = self.ys.copy()
        nonines_data[nines_ind] = float('nan')
        self.line.set_ydata(nonines_data)
        self.fig.canvas.draw()
        # print('UPDATE CALLED')

    def on_sensor_change_update(self):
        # print("MY_UPDATE IS CALLED")
        nines_ind = self.np.where(self.ys == 9999)
        nonines_data = self.ys.copy()
        nonines_data[nines_ind] = float('nan')
        self.line.set_ydata(nonines_data)
        self.show_home_view()
        self.ax.figure.canvas.flush_events()
        self.fig.canvas.draw()

    def show_home_view(self):
        self.ax.autoscale(enable=True, axis='x', tight=True)
        self.ax.set_xlim([self.xs[0], self.xs[-1]])
        self.ax.set_ylim(self.np.nanmin(self.ys) - 50,
                         self.np.nanmax(self.np.ma.masked_equal(self.ys, 9999, copy=False)) + 50)
        self.ax.margins(0.05, 0.05)
        self.pan_index = -1

    def ondelete(self, ind):
        # do not append if item already deleted
        if (self.ys[ind] != 9999):
            # print("On Delete Called on index", ind)
            self.deleted.append({ind: [self.xs[ind], self.ys[ind]]})

    def onpan(self, p_index):
        # print("ON PAN")
        pan_lim = len(self.xs) // self.jump_step
        # check for the edge case when the remainder of the division is 0
        # i.e. the number of data points divided by the jump step is a whole number
        if (len(self.xs) % self.jump_step == 0):
            pan_lim = pan_lim - 1
        if(self.pan_index>pan_lim):
            self.onDataEnd.fire("You've panned through all of the data")
        self.pan_index = self.np.clip(self.pan_index, 0, pan_lim)  # Limit pan index from growing larger than needed
        p_index = self.pan_index

        left = self.jump_step * p_index
        right = self.jump_step * p_index + self.jump_step
        if (right > len(self.xs)+self.jump_step):

            return
        # limiting left and right range to the size of the data
        if (right > len(self.xs) - 1):
            right = len(self.xs) - 1
            left = right - self.jump_step

        if (left < 0):
            left = 0
            right = left + self.jump_step
            self.pan_index = 0
        # define time range
        self.ax.set_xlim(self.xs[left], self.xs[right])
        # find Y range but exclude 9999s and nans
        # 50 for padding
        self.ax.set_ylim(self.np.nanmin(self.ys[left:right]) - 50,
                         self.np.nanmax(self.np.ma.masked_equal(self.ys[left:right], 9999, copy=False)) + 50)

    def onselect(self, verts):
        path = Path(verts)
        self.ind = self.np.nonzero(path.contains_points(self.xys))[0]

        for i in self.ind:
            self.bulk_deleted.append({i: [self.xs[i], self.ys[i]]})
            self.ys[i] = 9999
            # self.ondelete(i)
        self.on_bulk_delete()

    def disconnect(self):
        self.lasso.disconnect_events()

    def on_bulk_delete(self):
        self.text.set_text(
            'bulk items deleted')
        nines_ind = self.np.where(self.ys == 9999)
        nonines_data = self.ys.copy()
        nonines_data[nines_ind] = float('nan')
        self.line.set_ydata(nonines_data)
        self.fig.canvas.draw()

    def getDeleted(self):
        return self.deleted

    def next_pointer(self, data_ar, outl_ar, pointer, inc):
        if (data_ar[outl_ar[pointer]] != 9999):
            pointer += inc

            if pointer > len(outl_ar) - 1:
                pointer = len(outl_ar) - 1
                self.onDataEnd.fire("This was the last outlier. You can click the same channel again to find smaller outliers")
        # skip over deleted values
        while data_ar[outl_ar[pointer]] == 9999:
            # print("skipping data", data_ar[outl_ar[pointer]])
            # print("skipping index", pointer)
            # print("POINTER", pointer)
            # print("LEN of OUTLIER ARRAy", len(outl_ar))
            pointer += inc
            if pointer > len(outl_ar) - 1:
                pointer = len(outl_ar) - 1
                self.onDataEnd.fire("This was the last outlier. You can click the same channel again to find smaller outliers")
                break
        return pointer

    def next_pointer_all(self, data_ar, pointer, inc):
        if (data_ar[pointer] != 9999 and not self.np.isnan(data_ar[pointer])):
            pointer += inc
            if pointer > len(data_ar) - 1:
                pointer = len(data_ar) - 1
                self.onDataEnd.fire("This was the last data point")
        while (data_ar[pointer] == 9999 or self.np.isnan(data_ar[pointer])):
            pointer += inc
            if pointer > len(data_ar) - 1:
                pointer = len(data_ar) - 1
                self.onDataEnd.fire("This was the last data point")
                break
        return pointer

    # offset all the data starting with from the beginning up to the provided date
    def offset_data(self, time, offset):
        """
        time -> ISO date.time string (e.g. '2005-02-25T03:30')
        offset -> Integer
        """
        indices = self.np.where(self.xs <= self.np.datetime64(time))
        # Do not add offset if the data point is 9999
        indices = self.np.where(self.ys[indices[0]] < 9999)
        self.ys[indices[0]] = self.ys[indices[0]] + offset
        self.update()

    @property
    def data(self):
        return self.ys

    # def __del__(self):
    #   class_name = self.__class__.__name__
    #   print (class_name, "destroyed")


# C#-like event handling so that our main program can receive messages from
# matplotlib events
# As per https://stackoverflow.com/questions/1092531/event-system-in-python
class EventHook(object):

    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        for handler in self.__handlers:
            handler(*args, **keywargs)

    def clearObjectHandlers(self, inObject):
        for theHandler in self.__handlers:
            if theHandler.im_self == inObject:
                self -= theHandler
