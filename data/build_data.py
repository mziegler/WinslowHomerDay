"""
Convert human-editable CSV files into JSON files, used by the web application.
"""

import json
import csv
from io import StringIO
from datetime import datetime




################################################################################
# CONFIG 


# behavior categories to include in the JSON file
categories = set(('G', 'M', 'W', 'C', 'E', 'F', 'H', 'I', 'P', 'S', 'V',)) #'A', 'L', 'O'

# time of first GPS point
firstGPStime = datetime(2014,1,24,5,36,14)

# seconds between each GPS point
intervalseconds = 60


class InFileNames:
    observations = 'behavior observation codes.csv'
    translations = 'behavior code translations.csv'
    mediafeatures = 'media features.json'
    gpstrack = 'GPS track.csv'
    pictures = 'pictures.csv'
    textbubbles = 'text bubbles.csv'


class OutFileNames:
    behavior = 'behavior.json' # observations + translations
    behaviorcsv = 'behavior observation data.csv'
    media = 'media.js' # pictures, videos, text, media features







# monkey patch json encoder to format floats
from json import encoder
encoder.FLOAT_REPR = lambda o: format(o, '.5f')


    


################################################################################
# GPS track

with open(InFileNames.gpstrack) as f:
    reader = csv.reader(f, skipinitialspace=True)
    GPStrack = [(float(lat[:9]), float(lon[:10])) for (lat,lon) in list(reader)[1:]]






################################################################################
# BEHAVIOR FILES (observations + translations) -> (behavior samples.json + behavior samples.csv)

def parsetime(timestr):
    """
    Get the time from a string, ignore the date.
    (Return a datetime with the date of the first GPS point.)
    """
    
    # take out the date (get only the last space-separated part)
    timestr = timestr.split()[-1]
    time = datetime.strptime(timestr, '%H:%M:%S').time()
    
    return datetime.combine(firstGPStime.date(), time)



def getTimeInterval(time):
    """
    Get start and end points on the GPS track, of the time interval containing "time".
    """
    
    index = int((time - firstGPStime).total_seconds() / intervalseconds)
    interval = GPStrack[index:index+2]
    
    if len(interval) == 2:
        return interval
    
    # if the time is past the last GPS point, return an interval with just the last GPS point    
    else:
        return (GPStrack[-1], GPStrack[-1])




def getGPSCoords(time):
    """
    Get a geographical point along Winslow Homer's GPS track, by linear interpolation
    """
    
    # get start and stop
    start, stop = getTimeInterval(time)
    
    timediff = (time - firstGPStime).total_seconds()
    proportion = (timediff % intervalseconds) / float(intervalseconds)
    
    latdelta = (stop[0] - start[0])
    lat = (proportion * latdelta) + start[0]
    
    londelta = (stop[1] - start[1])
    lon = (proportion * londelta) + start[1]
    
    return (lat, lon)





def loadTranslationsFile():
    """
    Load the translations file, return a list of dicts with the fields in the file
    """
    
    with open(InFileNames.translations) as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        return list(reader)





def loadObservationFile(translations=None):
    """ 
    Load the observations file, return a list with a dict for each observation
    record, and a set with all of the unique behavior codes.
    
    
    """
    
    # ordered list of observations in file
    observations = [] 
    
    # set of codes we've seen
    codes = set() 
    
    
    with open(InFileNames.observations) as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        
        for line in reader:  
            # look up GPS coordinates from timestamp
            line['loc'] = getGPSCoords(parsetime(line['timestamp']))
        
            # add a 'time' field without the date, to display to user
            line['time'] = line['timestamp'].split()[1]
        
            observations.append(line)
            codes.add(line['code'])
    
    
    return observations, codes
    
    
    


def filterObservationsTranslations():
    """ 
    Return (observations, translations) list containing the intersection 
    (inner join) of the observations and translations, and only in the 
    configured categories.
    """
    
    translations = loadTranslationsFile()
    observations, obs_code_set = loadObservationFile()
    
       
    # Find codes that occur in the observations, and are in the right categories.
    # Make a {code : translation-fields} 2-dimensional dict.
    translations_dict = {
        t['code'] : t
        for t in translations
        if  (t['code'] in obs_code_set)  and  (t['category'].upper() in categories)   }
    
    
    # Find observations that have a translation.
    observations = list(filter(lambda o: o['code'] in translations_dict, observations))
    
    
    return observations, translations_dict
    
    
    
    
    

def writeBehaviorJSON():
    """
    Write behavior JSON file, with observations and translations joined.
    """

    observations, translations_dict = filterObservationsTranslations()
    
    # join together observations with translations
    behavior_list = [
        {
            'time': o['time'],
            'loc': o['loc'],
            'text': translations_dict[o['code']]['english'],
            'cat': translations_dict[o['code']]['category'],
            'score': translations_dict[o['code']]['interestingness']
        }
        for o in observations
    ]
    
    
    with open(OutFileNames.behavior, 'w') as f:
        json.dump({'behavior':behavior_list}, f)
    
         



def buildBehavior():
    writeBehaviorJSON()
    
    
    
    
    
    
    
    
def loadPictureCSV():
    """
    Load pictures from CSV file, and calculate coordinates for each picture
    from the timestamp.  Return a list of dicts, one dict for each picture.
    """
    
    with open(InFileNames.pictures) as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        

        pictures = list(reader)
        
        # look up GPS coordinates from timestamp
        for p in pictures:
            p['loc'] = getGPSCoords(parsetime(p['timestamp']))

    return pictures
        



def pictureJSON():
    """
    Format pictures into JSON
    """
    pictures = loadPictureCSV()
    
    return [
        {
            'uri': p['filename'],
            'loc': p['loc'],
            'cap': p['english'],
        }
    
        for p in pictures
    ]
    
    




def loadTextbubbleCSV():
    with open(InFileNames.textbubbles) as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        
        bubbles = list(reader)
        
        # look up GPS coordinates from timestamp
        for b in bubbles:
            b['loc'] = getGPSCoords(parsetime(b['timestamp']))
                    
                    
        return bubbles



def textbubbleJSON():
    bubbles = loadTextbubbleCSV()

    return [
        {
            'loc': b['loc'],
            'title': b['english_title'],
            'text': b['english_text'],
        }
        
        for b in bubbles
    ]

    




def mediaFeaturesJSON():
    with open(InFileNames.mediafeatures) as f:
        return json.load(f)






    
def buildMedia():
    with open(OutFileNames.media, 'w') as f:
        
        media = {
            'pictures': pictureJSON(),
            'textbubbles': textbubbleJSON(),
        }
        
        media.update(mediaFeaturesJSON())
        
        f.write('var media=')
        f.write(json.dumps(media))
        f.write(';')

        
        
    
    
    
    
    
    
    
    
    
    

if __name__ == '__main__':
    buildBehavior()
    buildMedia()
