
# coding: utf-8

# In[1]:

import xml.etree.cElementTree as ET
import pprint
import csv
import re
from collections import defaultdict
import codecs
import cerberus  #conda-forge/cerberus, version 1.0.1
import schema    #schema information stored in schema.py file for brevity purposes


# In[4]:

filename = "san-jose_california.osm"  #update filepath as necessary


# In[3]:

def count_tags(filename):
    '''
    Tis function counts the different tag labels in an XML file and returns
    a dictionary showing the number of times each tag label appears
    '''
    dictionary = {}
    treeiter = ET.iterparse(filename)
    for event, child in treeiter:
        if child.tag in dictionary:
            dictionary[child.tag] += 1
        else:
            dictionary[child.tag] = 1
    print dictionary
    
    return dictionary


# In[6]:

def key_type(element, keys):
    '''
    The key_type function and the following process_map functions were used to
    see what kind of formatting the keys ("k"-attribute) were in by matching against
    pre-defined regular expressions.
    '''
    lower = re.compile(r'^([a-z]|_)*$')
    lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
    problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

    if element.tag == "tag":
        
        if lower.search(element.attrib['k']) is not None:
            keys['lower'] += 1
            return keys
        if lower_colon.search(element.attrib['k']) is not None:
            keys['lower_colon'] += 1
            return keys
        if problemchars.search(element.attrib['k']) is not None:
            keys['problemchars'] += 1
            return keys
        else:
            keys['other'] += 1
            return keys
        
    return keys

def process_map(filename):
    keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
    for _, element in ET.iterparse(filename):
        keys = key_type(element, keys)

    return keys


# In[8]:

def audit_street_type(street_types, street_name):
    '''
    This function creates a dictionary matching the last word in a street address to the number of times
    that word occurs if the word is not in our expected list of entries. Then we make a decision
    to convert those words using the update_name function below.
    '''
    street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
    expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Way", "Terrace", "Circle", "Expressway"]
    
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)
            
def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types


# In[11]:

def update_name(name, mapping):
    
    names = name.split(' ')
    if names[-1] in mapping:    #check if the last word has a corresponding update
        names[-1] = mapping[names[-1]]
        return " ".join(names)
    else:
        return name


# In[12]:

mapping = { "St": "Street",
            "St.": "Street",
            "street": "Street",
            "court": "Court",
            "Rd.": "Road",
            "Ln": "Lane",
            "Sq": "Square",
            "Ave": "Avenue",
            "ave": "Avenue",
            "Blvd": "Boulevard",
            "Boulvevard": "Boulevard",
            "Hwy": "Highway",
            "Cir": "Circle"
            }


# In[13]:

def check_k(name):
    '''
    This function converts the key from old_amenity to old:amenity in the 2 entries
    where old_amenity occurs in the San Jose dataset
    '''
    
    if name == "old_amenity":
        return "old:amenity"
    else:
        return name


# In[ ]:

def check_state(element):
    '''
    element: input XML tag from California OpenStreetMap data
    
    This function checks if the tag key is "state". If it is,
    then it will return "CA" as the value to be associated with
    the key. If not, then it will return the original tag value.
    '''
    
    if element.attrib['k'] == "addr:state":
        return "CA"
    if element.attrib['k'] == "is_in:state":
        return "CA"
    else:
        return element.attrib['v']


# In[2]:

def correct_zip(value):
    
    zip_re = re.compile(r'\d{5}')
    match = zip_re.search(value)
    
    if match is not None:
        return match.group()
    else:
        return value


# In[ ]:

# The following code creates 5 .csv output files from the XML file. These files can then be imported
# into an SQL database using a program such as sqlite3.

OSM_PATH = filename

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
    # YOUR CODE HERE
    if element.tag == 'node':
        for attribute in node_attr_fields:
            node_attribs[attribute] = element.attrib[attribute]
        for tag in element.iter('tag'):
            if problem_chars.search(tag.attrib['k']) is not None:  #if a problem character is detected in key
                continue                                            #move on to the next entry
            else:
                tagDict = {}
                tagDict['id'] = element.attrib['id']
                corrected_k = check_k(tag.attrib['k'])
                if LOWER_COLON.search(corrected_k) is not None:
                    colonLoc = corrected_k.index(':')
                    tagDict['key'] = corrected_k[colonLoc + 1 :]
                    tagDict['type'] = corrected_k[ : colonLoc]
                else:
                    tagDict['key'] = corrected_k
                    tagDict['type'] = 'regular'
                if is_street_name(tag):    #if tag is a street name, update name if necessary
                    tagDict['value'] = update_name(tag.attrib['v'],mapping)
                elif tagDict['key'] == 'postcode':
                    tagDict['value'] = correct_zip(tag.attrib['v'])
                else:
                    tagDict['value'] = check_state(tag)
                tags.append(tagDict)
        return {'node': node_attribs, 'node_tags': tags}
        
    elif element.tag == 'way':
        for attribute in way_attr_fields:
            way_attribs[attribute] = element.attrib[attribute]
            
        ndCounter = 0
        for node in element.iter('nd'):
            ndDict = {}
            ndDict['id'] = element.attrib['id']
            ndDict['node_id'] = node.attrib['ref']
            ndDict['position'] = ndCounter
            way_nodes.append(ndDict)
            ndCounter += 1
        for tag in element.iter('tag'):
            if problem_chars.search(tag.attrib['k']) is not None:
                continue
            else:
                tagDict = {}
                tagDict['id'] = element.attrib['id']
                corrected_k = check_k(tag.attrib['k'])
                if LOWER_COLON.search(corrected_k) is not None:
                    colonLoc = corrected_k.index(':')
                    tagDict['key'] = corrected_k[colonLoc + 1 :]
                    tagDict['type'] = corrected_k[ : colonLoc]
                else:
                    tagDict['key'] = corrected_k
                    tagDict['type'] = 'regular'
                if is_street_name(tag):    #if tag is a street name, update name if necessary
                    tagDict['value'] = update_name(tag.attrib['v'],mapping)
                elif tagDict['key'] == 'postcode':
                    tagDict['value'] = correct_zip(tag.attrib['v'])
                else:
                    tagDict['value'] = check_state(tag)
                tags.append(tagDict)

        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file,         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file,         codecs.open(WAYS_PATH, 'w') as ways_file,         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file,         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


# In[ ]:

# Note: Validation is ~ 10X slower. For the project consider using a small
# sample of the map when validating.  

process_map(OSM_PATH, validate=True)


# In[ ]:



