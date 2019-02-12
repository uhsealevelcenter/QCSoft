import numpy as np
import re

class DataExtractor:
    '''
    Takes a path to the monp dat file
    '''

    def __init__(self, filename):
        self.in_file = open(filename, 'r') #t1091803.dat. sgana1801.dat
        self.headers = []
        self.frequencies = []
        self.refs = []
        self.sensor_ids = []
        self.init_dates=[]
        self.data_all = {}
        self.infos_time_col = {}
        self.prev_date = 0

        self.parse_file(filename)

    def is_header(self, arg):
        """
        Check if the line scanned is a header
        The checker is looking for word "LONG" in that line of text
        According to Fee, every header of every station has LONG in it
        """
        #if (line[0][0].isdigit() and not '99999' in line):
        return bool('LONG' in arg)

    def split_by_n(self, n, num):
            return [num[i:i+n] for i in range(0, len(num), n)]

    def missing_dates(self, L):
        start, end = L[0], L[-1]
        return sorted(set(range(start, end + 1)).difference(L))

    def parse_file(self,filename):
        listoflists = []
        a_list = []
        counter = 0

        for line in self.in_file:
            a_list.append(line)
            if(line.startswith('99999')): #should probably use 80*"9"
                # print "Channel End, append a new channel"
                a_list.remove(a_list[-1])
                listoflists.append((counter,list(a_list)))
                a_list = []
                counter += 1

            if self.is_header(line):
                self.headers.append(line)
                self.frequencies.append(line.split()[-4])
                self.refs.append(re.search('REF=([^ ]+) .*',line).group(1))
        for header in self.headers:
             # safeguarding against the case a station number ever becomes a 4 digit
             # search for digits in the first element of the header and put the together
            station_num = ''.join(map(str,[int(s) for s in header.split()[0][0:4] if s.isdigit()]))
            self.sensor_ids.append(station_num+header.split()[0][-3:])
            # self.sensor_ids.append(header.split()[0][0:3]+header.split()[0][-3:])
            # self.sensor_ids.append(header.split()[0][-3:])

        # because file ends with two lines of 9s there is an empty list that needs to be
        # deleted
        del listoflists[-1]



        for sensor in range(len(self.sensor_ids)):
            data = [] # only sea level measurements (no time)
            info_time_col = []
            # if(filename.split('/')[-1][0] == 't'):
            #     init_date_lst=(listoflists[sensor][1][1][:20].split()[1:4]) #[1:4] if loading a 'ts' file
            # else:
            #     init_date_lst=(listoflists[sensor][1][1][:20].split()[2:5]) #[2:5] if loading a 'monp' file
            #     if(len(init_date_lst[0])>4):
            #         init_date_lst.pop()
            #         init_date_lst.append(init_date_lst[1])
            #         init_date_lst[1] = init_date_lst[0][4:]
            #         init_date_lst[0] = init_date_lst[0][0:4]

            if(float(self.frequencies[sensor])>=6.0):
                lines_per_day=int(1440/12/int((self.frequencies[sensor])))
            else:
                lines_per_day=int(1440/15/int((self.frequencies[sensor])))

            pre_text = listoflists[sensor][1][1:][0][0:15]

            # 1) Figure out the missing date (HARD CODING FOR NOW)
            m_length = int(listoflists[sensor][1][0:][0][77:79])
            l = [i for i in range(m_length+1)]

            print(m_length)

            month_ar = [0] # need to iniate with 0 because we need to check if the first
                        # day in a month is missing

            # go through every line of data
            for l in range(len(listoflists[sensor][1][1:])):
                # find first row of each month to get all dates in the file
                if(l%lines_per_day == 0):
                    month_ar.append(int(listoflists[sensor][1][1:][l][15:17]))
            # add upper month range + 1 to check if there are any consecutive days
            # including the last date missing
            if(month_ar[-1]!= m_length):
                month_ar.append(m_length+1)
            #Copy the list with all the data so that we can modify it
            lines_copy = listoflists[sensor][1][1:]
            # Check for missing date and reset the comparison array to default [0]
            missed_dates_ar = self.missing_dates( month_ar )
            print("Missing dates", missed_dates_ar)
            month_ar[0]

            # There might be multiple days missing so need to loop through all of them
            for day in missed_dates_ar:
                missing_date = day
                missing_date_str = '{:>2}'.format(str(missing_date))


                # Create and format an array of lines with dates and missing data
                bad_data_ar = []
                # 2) Add lines_per_day lines with 9999 values and increase the line counter
                for l in range(lines_per_day):
                    if(float(self.frequencies[sensor])>=6.0):
                        # print(pre_text+str(missing_date_str)+" "+'{:>2}'.format(str(l))+" 9999"*12)
                        bad_data_ar.append(pre_text+str(missing_date_str)+" "+'{:>2}'.format(str(l))+" 9999"*12+"\n")
                    else:
                        # print(pre_text+str(missing_date_str)+" "+'{:>2}'.format(str(l))+"9999"*15)
                        bad_data_ar.append(pre_text+str(missing_date_str)+" "+'{:>2}'.format(str(l))+"9999"*15+"\n")
                # 3) prepend the above print statement to the listoflists[sensor][1][1:]
                # insert the missing date with missing data
                for b in range(len(bad_data_ar)):
                    lines_copy.insert((missing_date-1)*lines_per_day+b, bad_data_ar[b])
                bad_data_ar = []


            # init_date_lst=listoflists[sensor][1][1][8:17].split()
            init_date_lst=lines_copy[0][8:17].split()
            if(len(init_date_lst)>2):
                year  = init_date_lst[0]
                month = init_date_lst[1]
                day   = init_date_lst[2]
                # for i in range(len(init_date_lst)):
                #     if(len(init_date_lst[i])==1):
                #         init_date_lst[i]="0"+init_date_lst[i]
                # if(len(init_date_lst[0])<4):
                #     init_date_lst[0]="20"+init_date_lst[0] #assuming no data from the '90s. Check with Fee
            else:
                month = init_date_lst[0][-2:]
                year = init_date_lst[0][:-2]
                day = init_date_lst[1]
                init_date_lst[1] = init_date_lst[0][4:]
            if(len(day)==1):
                day="0"+day
            if(len(month)==1):
                month="0"+month
            if(len(year)<4):
                year="20"+year
            init_date=np.datetime64("-".join([year, month, day])+'T00:00:00.000000')
            self.init_dates.append(init_date)


            # for line in listoflists[sensor][1][1:]:
            for line in lines_copy:
                # Read each row of data into a list of floats
                # and also save the non-sensor data part (0:21) for the output file
                info_time_col.append(line[:20])

                # if(int(info_time_col[-1][15:17])-self.prev_date>1):
                #     self.prev_date = int(info_time_col[-1][15:17])
                # print("diff",int(info_time_col[-1][15:17])-self.prev_date)
                # print("date",int(info_time_col[-1][15:17]))
                if(float(self.frequencies[sensor])>=6.0):
                    # fields=line[20:].split() # for 5 digit data format
                    fields=self.split_by_n(5,line[20:].rstrip('\n')) # for 5 digit data format
                    # if(len(info_time_col)>1):
                    #     if((int(info_time_col[-1][15:17])-int(info_time_col[-2][15:17]))>1):
                    #         print("diff", int(info_time_col[-1][15:17])-int(info_time_col[-2][15:17]))
                    #         for m in range(1440/15/int(self.frequencies[sensor])):
                    #             info_time_col[-2] = "s 109PRS  1810  1  0"
                    #         fields = '9'*60
                else:
                    fields = self.split_by_n(4,line[20:].rstrip('\n')) # for 4 digit data format
                for s in fields:
                    if(s=='****' or s==' ****' or s=='*****'):
                        fields[fields.index(s)] = '9999'
                row_data = [float(x) for x in fields]

                # And add this row to the
                # entire data set.
                data.append(row_data)
            # # Finally, convert the "list of
            # # lists" into a 2D array.
            # self.infos_time_col.append(info_time_col)
            self.infos_time_col[self.sensor_ids[sensor][-3:]] = info_time_col
            # self.data_all.append(np.array(data))
            self.data_all[self.sensor_ids[sensor][-3:]] = np.array(data)

        self.in_file.close()





    # listoflists = []
    # a_list = []
    #


    # in_file = open(self.filepath, 'r') #t1091803.dat. sgana1801.dat
    #
    # # Read and ignore header lines
    # # header1 = f.readline()
    # headers = []
    # frequencies = []
    # start_date = []
    # counter = 0
    # sensor_ids = [] # station number + sensor
    # for line in in_file:
    #     #print repr(line)
    #     #
    #     a_list.append(line)
    #     if(line.startswith('99999')): #should probably use 80*"9"
    #         # print "Channel End, append a new channel"
    #         a_list.remove(a_list[-1])
    #         listoflists.append((counter,list(a_list)))
    #         a_list = []
    #         counter += 1
    #
    #     if is_header(line):
    #         headers.append(line)
    #         frequencies.append(line.split()[-4])
    #     #line.split()
    # for header in headers:
    #     sensor_ids.append(header.split()[0][0:3]+header.split()[0][-3:])
    #
    # station_name = header[:6]
    #
    # # because file ends with two lines of 9s there is an empty list that needs to be
    # # deleted
    # del listoflists[-1]
    #
    # # extract the data only, test for one
    # listoflists[0][1][1][20:].split()
    #
    #
    #
    #
    # # listoflists[0][1][1:] ---> all data, excluding header for a particular sensor
    #
    # sensor=1
    # init_date_lst=(listoflists[sensor][1][1][:20].split()[2:5]) #[1:4] if loading a 'ts' file
    # for i in range(len(init_date_lst)):
    #     if(len(init_date_lst[i])==1):
    #         init_date_lst[i]="0"+init_date_lst[i]
    # if(len(init_date_lst[0])<4):
    #     init_date_lst[0]="20"+init_date_lst[0] #assuming no data from the '90s. Check with Fee
    # init_date=np.datetime64("-".join(init_date_lst))
    #
    # # print(arr)
    # data = [] # only sea level measurements (no time)
    # info_time_col = []
    # for line in listoflists[sensor][1][1:]:
    #     # Read each row of data into a list of floats
    #     # and also save the non-sensor data part (0:21) for the output file
    #     info_time_col.append(line[:20])
    #     if(float(frequencies[sensor])>=6.0):
    #         fields=line[20:].split() # for 5 digit data format
    #     else:
    #         fields = split_by_n(4,line[20:].strip()) # for 4 digit data format
    #     row_data = [float(x) for x in fields]
    #     # And add this row to the
    #     # entire data set.
    #     data.append(row_data)
    #
    #
    # # Finally, convert the "list of
    # # lists" into a 2D array.
    # data = np.array(data)
    # in_file.close()
