#tappedout_reader.py
#encoding: utf-8

#given a tappedout URL, reads the cards in the deck, and creates a JSON file that can represent the deck in Tabletop Simulator.
#Creates seperate decks for tokens and double faced-versions of double-faced cards (if needed).
#Does not currently allow for the printing to be selected. TODO determine which printing is used

# ======= imports ============
from urllib.request import urlopen, Request #webpage downloads
import re #regex
import time #for sleeping to be polite
import sys #command line arguments

# ====== constants =============
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'} #spoofed browser headers so tappedout doesn't think I'm a bot... :(
POLITENESS_DELAY = 0.1 #scryfall has nicely asked me to wait 100ms between requests.
X_SPACE =  2.5  #padding between decks in the X direction, in unknown units. experimentally determined to be a good value
DEFAULT_BACK_URL = 'i.imgur.com/LdOBU1I.jpg'

def main():
    # ========= command line arguments =========
    usage_string = "Usage: python tappedout_reader.py <tappedout url> <output file name/path> [options]\n\t\
                    Options:\n\t\
                    -cb [url]                       : custom card back image URL\
                    -s [small | normal | large]     : card image size (up/downscaled by TTS, influences quality)"
    
    num_args = len(sys.argv)
    if num_args < 3:
        print(usage_string)
        return
    
    #process required arguments
    TAPPED_URL = sys.argv[1]
    OUT_PATH = sys.argv[2]
    if OUT_PATH[-5:].lower() != '.json':
        OUT_PATH = OUT_PATH+'.json'
    
    #process optional arguments
    i = 3
    BACK_URL = DEFAULT_BACK_URL
    IMAGE_SIZE = 'normal'
    while i < num_args:
        if sys.argv[i] == '-cb':        #custom card back URL
            if num_args <= i+1:
                print(usage_string)
                return
            BACK_URL = sys.argv[i+1]
            i+=1
        
        if sys.argv[i] == '-s':         #image size specification
            if num_args <= i+1:
                print(usage_string)
                return
            provided_size = sys.argv[i+1].lower()
            if provided_size in ['small','normal','large']:
                IMAGE_SIZE = provided_size
            else:
                print(usage_string)
                return
        i+=1
        #end loop
    createDeckFile(TAPPED_URL, OUT_PATH, BACK_URL, IMAGE_SIZE)

def createDeckFile(TAPPED_URL, OUT_PATH, BACK_URL, IMAGE_SIZE):
    # ====== setup ==============
    card_names = []
    cmdr_names = []
    cmdr_true_names = [] #support double-sided commanders
    cmdr_fronts = []
    main_names = [] #double sided card names are different between scryfall and tappedout, scryfall's are better and are thus called "true" elsewhere
    main_fronts = []
    double_names = []
    double_fronts = []
    double_backs = []
    token_names = []
    token_fronts = []
    
    if OUT_PATH[-5:].lower() != '.json':
        OUT_PATH = OUT_PATH+'.json'
    
    DOWNLOAD_PATH = '../decks/'+OUT_PATH
    OUT_PATH = '/var/www/html/decks/'+OUT_PATH
    deckFile = DeckFile(OUT_PATH)
    deckFile.start()
    
    if BACK_URL == "" or BACK_URL == None or BACK_URL is None:
        BACK_URL = DEFAULT_BACK_URL

    # ====== get card names ==============
    print("Fetching card names from tappedout...")
    try:
        tapped_request = Request(url=TAPPED_URL, headers=HEADERS)
        tapped_html = urlopen(tapped_request).read().decode("utf-8") #assuming utf-8 but it's fine
    except:
        return "ERROR: Could not open tappedout URL: '"+TAPPED_URL+"'. Double check the URL. If this continues, tappedout has likely increased their ability to refuse service to bots. I'm a second class citizen :("
    #get list of card names from tappedout. for cards present multiple times, just add the name multiple times.
    card_plates = re.findall("boardContainer-main.*?>", tapped_html) #"plates" as in nameplates; getting unique strings from HTML for each card
    card_indices = [tapped_html.find(plate) for plate in card_plates] #locate each unique card in the page
    endpoints = card_indices #want to use indices to surround each card nameplate, need one more endpoint to surround final card
    endpoints.append(len(tapped_html)) #the end of the page should suffice :)
    card_regions = [tapped_html[endpoints[i]:endpoints[i+1]] for i in range(len(endpoints)-1)] #get the full nonsense-ridden html describing each card

    for region_n,region in enumerate(card_regions):
        name = re.findall("data-orig=\".*?\"", region)[0][11:-1] #lots of magic numbers, but: we find the field containing the card name (data-orig) and trim the unwanted characters
        name = cleanName(name)
        quantity = int(re.findall("data-qty=\".*?\"", region)[0][10:-1])
        for j in range(quantity):
            card_names.append(name)
    
    #get commanders/companions! they do not use the same format if put on display.
    cmdr_plates = re.findall('data-name=".*?[\S\W].*?<img class="commander-img"', tapped_html)
    cmdr_name_regions = [re.findall('data-name=".*?"', plate)[0] for plate in cmdr_plates]
    cmdr_names = [cleanName(name[11:-1]) for name in cmdr_name_regions]
    
    # ====== get card images ==============
    #get front and back images for all card names. 'main' deck has the front face of all cards, and gives them a static back. 'double' deck has only double-sided cards, and includes both sides.
    #this code is EVIL because if you're running 24 islands it will make scryfall api calls 24 times, once for each island. this is unnecessary and wasteful but I just want it to work at the moment
    print("Using Scryfall API to get card image URLs...")
    num_main_cards = len(card_names)
    for i,name in enumerate(card_names+cmdr_names):
        #use scryfall api to get image URLs. add front url to main front list. if back is present, add correct faces to double front & back lists.
        sf_url = "http://api.scryfall.com/cards/named?exact="+name
        #print('\t'+sf_url) #for debugging urls
        try:
            sf_html = urlopen(sf_url).read().decode("utf-8") #the scryfall API ONLY uses utf-8, so we're not just assuming it here
        except:
            return "ERROR: Could not fetch card: '"+name+"', URL: '"+sf_url+"'. Sometimes a card is spelled wrong in the tappedout list, or maybe the card is too new. When scryfall has it, we should be able to find it."
        time.sleep(POLITENESS_DELAY) #I'm a good citizen, I promise (please disregard the comment above that might cause you to believe I'm a bad citizen)
        true_name = re.findall('"name":".*?"',sf_html)[0][8:-1]
        all_images = re.findall('"'+IMAGE_SIZE.lower()+'":".*?"',sf_html)
        
        assert len(all_images) > 0, "Error: Image of the specified size ('"+IMAGE_SIZE+"') not received from scryfall."
        
        front_url = all_images[0][len(IMAGE_SIZE)+4:-1]
        
        if i >= num_main_cards: #this is a commander/companion, should not put it in the main deck (for convenience)
            cmdr_true_names.append(true_name)
            cmdr_fronts.append(front_url)
        else:
            main_names.append(true_name)
            main_fronts.append(front_url)
        
        if len(all_images) > 1:    
            double_names.append(true_name)
            back_url = all_images[1][len(IMAGE_SIZE)+4:-1]
            double_fronts.append(front_url)
            double_backs.append(back_url)

    # ====== get token images ==============
    print("Reading token names/images from tappedout...")
    #TODO what if no tokens?
    #get images for all tokens generated by cards in the deck.
    token_region = re.findall('<td>Tokens</td>\n\t<td>.*?</td>', tapped_html)[0] #XXX THIS LINE OF CODE IS EXTREMELY, EXTREMELY FRAGILE. VERY LIKELY A POINT OF FAILURE IN THE FUTURE. (the regex is too specific)

    token_url_snippets = re.findall('data-image=".*?"', token_region)
    token_name_snippets = re.findall('data-name=".*?"', token_region)

    token_fronts = [snippet[12:-1] for snippet in token_url_snippets]
    for i,front in enumerate(token_fronts): #tappedout is weird, sometimes the urls omit 'http:' and just start with two slashes. we have to remove those.
        if front[0:2] == '//':
            token_fronts[i] = front[2:]
    token_names = [snippet[11:-1] for snippet in token_name_snippets]

    # ====== assemble TTS object ==============
    print("Assembling output JSON file...")
    #THIS IS WHERE THE MAGIC HAPPENS
    deckFile.addDeck(main_names, main_fronts, [BACK_URL], faceDown=True) #main deck! assume there will always be cards.
    #deckFile = DeckFile(OUT_PATH)
    if (len(cmdr_true_names) > 0):
        deckFile.addDeck(cmdr_true_names, cmdr_fronts, [BACK_URL]) #commander/companion cards, if any
    if (len(double_names) > 0):
        deckFile.addDeck(double_names, double_fronts, double_backs) #double sided deck, if any
    if (len(token_names) > 0):
        deckFile.addDeck(token_names, token_fronts, [BACK_URL]) #token deck, if any
    deckFile.finish()
    #DONE
    print("Done.")
    return DOWNLOAD_PATH

# ====== functions and classes ==============

def cleanName(name):
    newName = name = re.sub("&#39;", "'", name) #replace strange apostrophe encodings. may have to do this with more punctiation.
    newName = re.sub(" ", "-", newName) #replace spaces with dashes, as this sometimes (not always) causes problems. See "Acorn Harvest")
    newName = re.sub(",", "", newName) #remove commas. this might be causing issues in some urllib versions
    return newName
    
#usage: instantiate a DeckFile, giving it a file path. One can then call addDeck() any number of times, and MUST call finish to close the file.
#All decks added will be a part of one "saved object", and all decks will be adjacent to each other when loaded in Tabletop Simulator.
class DeckFile:
    def __init__(self, path):
        self.path = path
        self.file = None
        self.num_decks = 0
        self.started = False
        self.finished = False
    
    def start(self):
        if (self.started == False):
            self.file = open(self.path,"w")
            self.file.write('{"ObjectStates":[')
            self.started = True
        
    def addDeck(self, names, frontURLs, backURLs=None, faceDown=False): #back URLs is optional. if omitted, uses default back. if length is one, uses the one element for every card. otherwise, treats fronts and backs as pairs.
        if (self.started == False):
            self.start()
        num_cards = len(names)
        
        if num_cards == 1: #for some reason TTS doesn't like decks with only one card! we need to write 1-card decks as just cards.
            if backURLs != None:
                self.addCard(names[0],frontURLs[0],backURLs[0], faceDown)
            else:
                self.addCard(names[0],frontURLs[0], faceDown = faceDown)
            return
        
        if (self.num_decks > 0):
            self.file.write(',')
        self.file.write('\n\t{\n\t\t"Name":"DeckCustom",\n\t\t"ContainedObjects":[')
        for i in range(num_cards):
            if (i!=0):
                self.file.write(',')
            self.file.write('\n\t\t\t{"CardID":'+str(100*(i+1))+',"Name":"Card","Nickname":"'+names[i]+'","Transform":{"posX":0,"posY":0,"posZ":0,"rotX":0,"rotY":180,"rotZ":180,"scaleX":1,"scaleY":1,"scaleZ":1}}')
        self.file.write('\n\t\t],\n\t\t"DeckIDs":[')
        for i in range(num_cards):
            if (i!=0):
                self.file.write(',')
            self.file.write(str(100*(i+1)))
        self.file.write('],\n\t\t"CustomDeck":{')
        
        for i in range(num_cards):
            if (backURLs == None):
                backURL = DEFAULT_BACK_URL
            elif (len(backURLs) == 1):
                backURL = backURLs[0]
            else:
                backURL = backURLs[i]
            if (i!=0):
                self.file.write(',')
            self.file.write('\n\t\t\t"'+str(i+1)+'":{"FaceURL":"'+frontURLs[i]+'","BackURL":"'+backURL+'","NumHeight":1,"NumWidth":1,"BackIsHidden":true}')
        
        rotZ = '180' if faceDown else '0'
        
        self.file.write('\n\t\t},\n\t\t"Transform":{"posX":'+str(self.num_decks*X_SPACE)+',"posY":0,"posZ":0,"rotX":0,"rotY":180,"rotZ":'+rotZ+',"scaleX":1,"scaleY":1,"scaleZ":1}\n\t}')
        self.num_decks += 1
    
    def addCard(self, name, frontURL, backURL=None, faceDown=False):
        if (self.started == False):
            self.start()

        if (self.num_decks > 0):
            self.file.write(',')
        self.file.write('\n\t{\n\t\t"Name":"Card",')
        self.file.write('\n\t\t"Nickname":"'+name+'",')
        self.file.write('\n\t\t"CardID":100,')
        
        if (backURL == None):
            backURL = DEFAULT_BACK_URL
        
        rotZ = '180' if faceDown else '0'
        
        self.file.write('\n\t\t"CustomDeck":{')
        self.file.write('\n\t\t\t"1":{"FaceURL":"'+frontURL+'","BackURL":"'+backURL+'","NumHeight":1,"NumWidth":1,"BackIsHidden":true}')
        self.file.write('\n\t\t},\n\t\t"Transform":{"posX":'+str(self.num_decks*X_SPACE)+',"posY":0,"posZ":0,"rotX":0,"rotY":180,"rotZ":'+rotZ+',"scaleX":1,"scaleY":1,"scaleZ":1}\n\t}')
        
        self.num_decks += 1
    
    def finish(self):
        self.file.write('\n]}')
        self.file.close()
        self.finished = True

if __name__ == '__main__':
    main()
