#jumpstart_scraper.py
#scrapes tappedout decks of jumpstart card packs and chirns out JSON files for use with tabletop simulator

# ======= imports ============
from urllib.request import urlopen #webpage downloads
import re #regex
import time #for sleeping to be polite
from PIL import Image, ImageDraw, ImageFont #for creating the allocation deck

# ====== setup =============
base_url = "https://tappedout.net/mtg-decks/jumpstart-pack-"
card_cols = 15 #all packs end up in a single JSON/object, arranged in a grid with a number of columns determined here. number of rows is "however many it takes."
url_range = range(1,122) #upper bound is exclusive
url_suffix = "/"
SLEEP_FACTOR = 1 #I like the funny name
X_SPACE =  2.5  #padding between packs in the X direction, in unknown units. experimentally determined a good value
Z_SPACE = -3.5 #ibid but on Z axis
CARD_DIMS = (409,585) #optimal pixel dimensions for TTS card images

#create the output file
out_f = open("jumpstart_pack_grid.json","w")
out_f.write('{"ObjectStates":[\n') #prefix for the file

#prepare image creation stuff
FONT_SIZE = 30
CARD_BG_COLOR = (240,240,240)
CARD_TEXT_COLOR = (12,12,12)
card_font = ImageFont.truetype('Titillium/Titillium-Regular.otf',FONT_SIZE)


# ======== scraping ===========
#for each pack, get card list
for url_n in url_range:
    print("Processing pack number "+str(url_n)+"...")
    time.sleep(SLEEP_FACTOR) #pause so we're not DDOS'ing anyone    
    #combine URL pieces
    url = base_url+str(url_n)+url_suffix
    html = urlopen(url).read().decode("utf-8") #assuming utf-8 but it's fine
    
    #create allocation card image
    pack_description = re.findall('<p>.*?</p>',html)[2][3:-4]
    img = Image.new('RGB',CARD_DIMS,color=CARD_BG_COLOR)
    drawer = ImageDraw.Draw(img)
    drawer.text((100,200),pack_description,font=card_font,fill=CARD_TEXT_COLOR)
    drawer.text((150,300),str(url_n),font=card_font,fill=CARD_TEXT_COLOR)
    img.save('selection_cards/pack_'+str(url_n)+'_card.png')
    
    #parse the pack
    card_plates = re.findall("boardContainer-main.*?>", html) #"plates" as in nameplates; getting unique strings from HTML for each card
    card_indices = [html.find(plate) for plate in card_plates] #locate each unique card in the page
    endpoints = card_indices #want to use indices to surround each card nameplate, need one more endpoint to surround final card
    endpoints.append(len(html)) #the end of the page should suffice :)
    card_regions = [html[endpoints[i]:endpoints[i+1]] for i in range(len(endpoints)-1)] #get the full nonsense-ridden html describing each card
    quantities = []
    out_f.write('\t{\n\t\t"Name":"DeckCustom",\n\t\t"ContainedObjects":[\n')

    #for each card, extract desired information
    #want: card name, card quantity, image URL
    for region_n,region in enumerate(card_regions):
        name = re.findall("data-orig=\".*?\"", region)[0][11:-1] #lots of magic numbers, but: we find the field containing the card name (data-orig) and trim the unwanted characters
        quantity = int(re.findall("data-qty=\".*?\"", region)[0][10:-1])
        #face_url = re.findall("data-image=\".*?\"", region)[0][12:-1] #URL will be used later. I'm sacrificing runtime for memory and code simplicity/linearity.
        quantities.append(quantity) #python makes me lazy
        
        #we have the desired information. Now we must place it in a JSON file for TTS.
        for n in range(quantity):
            out_f.write('\t\t\t{"CardID":'+str((1+region_n)*100)+',"Name":"Card","Nickname":"'+name+'","Transform":{"posX":0,"posY":0,"posZ":0,"rotX":0,"rotY":180,"rotZ":180,"scaleX":1,"scaleY":1,"scaleZ":1}},\n')
    #trim the last comma
    out_f.seek(out_f.seek(0,1)-2) #change write position to ((get current write position) - 2)
    out_f.write('\n\t\t],\n\t\t"DeckIDs":[')
    
    #write the card ID for wach card present, in order, accounting for quantity
    for region_n, qty in enumerate(quantities):
        for q in range(qty):
            out_f.write(str(100*(1+region_n))+',')
    #trim last comma
    out_f.seek(out_f.seek(0,1)-1)
    out_f.write('],\n\t\t"CustomDeck":{\n')
    
    #for each card, extract and write face URL to file
    for region_n, region in enumerate(card_regions):
        face_url = re.findall("data-image=\".*?\"", region)[0][14:-1] #URL will be used later. I'm sacrificing runtime for memory and code simplicity/linearity.
        out_f.write('\t\t\t"'+str((1+region_n))+'":{"FaceURL":"'+face_url+'","BackURL":"https://s3.amazonaws.com/frogtown.cards.hq/CardBack.jpg","NumHeight":1,"NumWidth":1,"BackIsHidden":true},\n')
        #out_f.write('\t\t\t"'+str((1+region_n))+'":{"FaceURL":"'+'https://s3.amazonaws.com/frogtown.cards.hq/CardBack.jpg'+'","BackURL":"https://s3.amazonaws.com/frogtown.cards.hq/CardBack.jpg","NumHeight":1,"NumWidth":1,"BackIsHidden":true},\n')
    #trim last comma (it's followed by a newline at the moment, need to seek backwards 2 places)
    out_f.seek(out_f.seek(0,1)-2) #change write position to ((get current write position) - 2)
    column = (url_n-1) % card_cols
    row = (url_n-1) // card_cols
    out_f.write('\n\t\t},\n\t\t"Transform":{"posX":'+str(X_SPACE*column)+',"posY":0,"posZ":'+str(Z_SPACE*row)+',"rotX":0,"rotY":180,"rotZ":180,"scaleX":1,"scaleY":1,"scaleZ":1}\n\t},\n')
    
#trim last comma, wrap up file
out_f.seek(out_f.seek(0,1)-2) #change write position to ((get current write position) - 2)
out_f.write('\n]}')

# ======== CLOSE THE OUTPUT FILE ========
out_f.close()
