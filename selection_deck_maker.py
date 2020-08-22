#selection_deck_maker.py
#creates JSON for use with tabletop simulator

# ====== setup =============
base_url = "http://70.185.116.158/jumpstart_selection_cards/pack_"
url_range = range(1,122) #upper bound is exclusive
url_suffix = "_card.png"

#create the output file
out_f = open("jumpstart_selection_deck.json","w")
out_f.write('{"ObjectStates":[\n') #prefix for the file



# ======== writing ===========
#create single deck object in JSON
out_f.write('\t{\n\t\t"Name":"DeckCustom",\n\t\t"ContainedObjects":[\n')

#for each pack, create a card:
for url_n in url_range:      
    #add card to deck
    out_f.write('\t\t\t{"CardID":'+str(url_n*100)+',"Name":"Card","Nickname":"Pack '+str(url_n)+'","Transform":{"posX":0,"posY":0,"posZ":0,"rotX":0,"rotY":180,"rotZ":180,"scaleX":1,"scaleY":1,"scaleZ":1}},\n')
    
#trim the last comma
out_f.seek(out_f.seek(0,1)-2) #change write position to ((get current write position) - 2)
out_f.write('\n\t\t],\n\t\t"DeckIDs":[')

#write the card ID for each card present
for url_n in url_range:
    out_f.write(str(100*url_n)+',')
#trim last comma
out_f.seek(out_f.seek(0,1)-1)
out_f.write('],\n\t\t"CustomDeck":{\n')

#for each card, extract and write face URL to file
for url_n in url_range:
    #combine URL pieces
    face_url = base_url+str(url_n)+url_suffix
    out_f.write('\t\t\t"'+str(url_n)+'":{"FaceURL":"'+face_url+'","BackURL":"https://vignette.wikia.nocookie.net/hearthstone/images/c/c4/Card_back-Default.png/revision/latest/scale-to-width-down/150?cb=20140823204025","NumHeight":1,"NumWidth":1,"BackIsHidden":true},\n')
#trim last comma (it's followed by a newline at the moment, need to seek backwards 2 places)
out_f.seek(out_f.seek(0,1)-2) #change write position to ((get current write position) - 2)
out_f.write('\n\t\t},\n\t\t"Transform":{"posX":0,"posY":0,"posZ":0,"rotX":0,"rotY":180,"rotZ":180,"scaleX":1,"scaleY":1,"scaleZ":1}\n\t},\n')
    
#trim last comma, wrap up file
out_f.seek(out_f.seek(0,1)-2) #change write position to ((get current write position) - 2)
out_f.write('\n]}')

# ======== CLOSE THE OUTPUT FILE ========
out_f.close()
