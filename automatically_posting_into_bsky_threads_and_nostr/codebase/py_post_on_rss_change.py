#!/usr/bin/env python3
import feedparser
import json
import hashlib
import os
import requests
import re
import time

from atproto import Client, models
from bs4 import BeautifulSoup
from datetime import datetime
from threads import Threads
from pynostr.event import Event
from pynostr.relay_manager import RelayManager
from pynostr.key import PrivateKey


def build_nostr_entry(entry):
    ''' Take the entry dict and build a string to post to nostr
    '''
    
    skip_tags = SKIP_TAGS
    skip_tags.append("blog")
    skip_tags.append("documentation")

    
    toot_str = ''
    
    if "blog" in entry['tags']:
        toot_str += "New #Blog: "
    elif "documentation" in entry['tags']:
        toot_str += "New #Documentation: "
    
    toot_str += f"{entry['title']}\n"
    
    
    toot_str += f"\n\n{entry['link']}\n\n"
    
    # Tags to hashtags
    if len(entry['tags']) > 0:
        for tag in entry['tags']:
            if tag in skip_tags:
                # Skip the tag
                continue
            toot_str += f'#{tag.replace(" ", "")} '
        
    return toot_str

def build_hashtagless_text_post(entry):
    ''' Build a string detailing the post 
    
    Don't include hashtags - the output of this function
    is intended for platforms that don't (currently) use them
    
    Response doesn't include the link (because services like threads
    expects them to be provided seperately
    '''
    
    toot_str = ''
    if "blog" in entry['tags']:
        toot_str += "New Blog: "
    elif "documentation" in entry['tags']:
        toot_str += "New Documentation: "    

    toot_str += f"{entry['title']}\n"
    
    return toot_str
    

def create_Bluesky_Post(entry):
    ''' Post into Bluesky 
    '''
    try:
        text = build_hashtagless_text_post(entry)
        
        # Append the link
        text += f"\n{entry['link']}"

        facets = generate_facets_from_links_in_text(text)
        short_desc = ' '.join(entry['description'].split(" ")[0:25]).lstrip()
        
        # See whether there's a thumb
        if entry['thumb']:
            # fetch the thumb
            response = requests.get(entry['thumb'])
            img_data = response.content
            
            # Upload the image
            upload = BSKY_CLIENT.com.atproto.repo.upload_blob(img_data)
            
            embed_external = models.AppBskyEmbedExternal.Main(
                external=models.AppBskyEmbedExternal.External(
                    title=entry['title'],
                    description=short_desc,
                    uri=entry['link'],
                    thumb=upload.blob
                )
            )            
        else:
            
            # Create the embed card without a thumb
            embed_external = models.AppBskyEmbedExternal.Main(
                external=models.AppBskyEmbedExternal.External(
                    title=entry['title'],
                    description=short_desc,
                    uri=entry['link']
                )
            )
        
        if DRY_RUN == "Y":
            print("---- BSky -----")
            print(text)
            print(facets)
            print("---- /BSky -----")
            return True
    
        BSKY_CLIENT.com.atproto.repo.create_record(
            models.ComAtprotoRepoCreateRecord.Data(
                repo=BSKY_CLIENT.me.did,
                collection='app.bsky.feed.post',
                record=models.AppBskyFeedPost.Main(
                createdAt=datetime.now().isoformat(), 
                text=text, 
                embed=embed_external,
                facets=facets
                ),
            )
        )
                
        return True
    except Exception as e:
        print(f"Failed to post to Bluesky: {e}")
        return False
    

def create_Nostr_event(entry):
    ''' Publish into Nostr
    '''
    try:
        out_str = build_nostr_entry(entry)
        
        if DRY_RUN == "Y":
            print("---- Nostr ----")
            print(out_str)
            print("---- /Nostr ----")
            return True
        
        # Create the event
        event = Event(out_str)
        event.sign(NOSTR_PK.hex())
        
        NOSTR_RELAY.publish_event(event)
        NOSTR_RELAY.run_sync()
        return True
    except Exception as e:
        print(f"Submitting to Nostr failed: {e}")
        return False
    
def create_Threads_Post(entry):
    ''' Create a threads posting 
    
    '''
    # Build a message
    toot_str = build_hashtagless_text_post(entry)
    
    if DRY_RUN == "Y":
        print("---- Threads -----")
        print(toot_str)
        print(entry['link'])
        print("---- /Threads -----")
        return True
    
    try:
        threads = Threads(username=THREADS_USER, password=THREADS_PASS)

        created_thread = threads.private_api.create_thread(
                caption=toot_str,
                url=entry['link']
            )
        return True
    except Exception as e:
        print(f"Submitting to Threads failed: {e}")
        return False

def check_if_link_seen(mode, linkhash, storedhash, feed, network):
    ''' Check whether the current hashed URL has previously been seen/tooted
    
    The way this is checked depends on mode
    
    - PERURL: checks for a hashfile specific to the linked url
    - PERFEED: checks the content of a feed specific hashfile (provided via storedhash)
    
    Return: boolean
    '''
    
    if mode != "PERURL":
        # Per feed hashing
        if storedhash == linkhash:
            return True
        else:
            return False
        
    # Per-url hashing
    #
    hashfile = f"{feed['HASH_DIR']}/{network}/{linkhash}"
    return os.path.exists(hashfile)


def write_hash_to_storage(mode, linkhash, feed, hashtracker, firsthash, network, l):
    ''' Write the hash to statefile(s)
    '''
    # For per-url tracking, switch out the tracker file handle
    # and set firsthash to be the same as the linkhash
    hashfile = f"{feed['HASH_DIR']}/{network}/{linkhash}"
    hashtracker = open(hashfile,'w')
    firsthash = linkhash
        
    hashtracker.seek(0)
    hashtracker.truncate()
    hashtracker.write(l)
    return
    
    
def process_feed(feed):
    ''' Process the RSS feed and generate a toot for any entry we haven't yet seen
    '''
    
    storedhash = False
    hashtracker = False
    
    # This will be overridden as we iterate through
    firsthash = False

    # Load the feed
    d = feedparser.parse(feed['FEED_URL'])

    # Iterate over entries
    for entry in d.entries:
        
        
        POSTED = False
        
        # compare a checksum of the URL to the stored one
        # this is used to prevent us re-sending old items
        linkhash = hashlib.sha1(entry.link.encode('utf-8')).hexdigest()
        #print('{}: {}'.format(entry.link,linkhash))
        
        '''
        if check_if_link_seen(TRACKING_MODE, linkhash, storedhash, feed):
            print("Reached last seen entry")
            break
        '''
        
        # Load the summary
        soup = BeautifulSoup(entry.summary, 'html.parser')

        # See whether there's an image
        thumb = None
        img = soup.find("img")
        if img:
            thumb = img["src"]

        en = {}
        en['title'] = entry.title
        en['link'] = entry.link
        en['author'] = False       
        en['tags'] = []
        en['description'] = soup.get_text()
        en['thumb'] = thumb

        if hasattr(entry, "tags"):
            # Iterate over tags and add them
            [en['tags'].append(x['term']) for x in entry.tags]

        if INCLUDE_AUTHOR == "True" and hasattr(entry, "author"):
            en['author'] = entry.author

        #print(en)

        # Keep a record of the hash for the first item in the feed
        # misc/Python_mastodon_rss_bot#1
        if not firsthash:
            firsthash = linkhash
            
        THREADS_SEEN = check_if_link_seen(TRACKING_MODE, linkhash, storedhash, feed, 'threads')
        if not THREADS_SEEN and (THREADS_USER and create_Threads_Post(en)):
            write_hash_to_storage(TRACKING_MODE, linkhash, feed, hashtracker, firsthash, 'threads', en['link'])
            print(f"Posted to Threads: {en['link']}")
            POSTED = True

        NOSTR_SEEN = check_if_link_seen(TRACKING_MODE, linkhash, storedhash, feed, 'nostr')           
        if not NOSTR_SEEN and (DO_NOSTR and create_Nostr_event(en)):
            write_hash_to_storage(TRACKING_MODE, linkhash, feed, hashtracker, firsthash, 'nostr', en['link'])
            print(f"Posted to Nostr: {en['link']}")  
            POSTED = True
        
        BSKY_SEEN = check_if_link_seen(TRACKING_MODE, linkhash, storedhash, feed, 'bsky')
        if not BSKY_SEEN and (BSKY_USER and create_Bluesky_Post(en)):
            write_hash_to_storage(TRACKING_MODE, linkhash, feed, hashtracker, firsthash, 'bsky', en['link'])
            print(f"Posted to Bluesky: {en['link']}")  
            POSTED = True
            
        '''
        # Send the toot
        #
        # TODO: This will currently cause an exception, needs replacing
        if send_toot(en):
            # If that worked, write hash to disk to prevent re-sending
            write_hash_to_storage(TRACKING_MODE, linkhash, feed, hashtracker, firsthash)
        '''
        if POSTED:
            time.sleep(1)

    if hashtracker:
        hashtracker.close()


def generate_facets_from_links_in_text(text):
    ''' Based on logic in
        https://github.com/GanWeaving/social-cross-post/blob/main/helpers.py
        
        Generate atproto facets for each URL in the text
    '''
    facets = []
    for match in URL_PATTERN.finditer(text):
        facets.append(gen_link(*match.span(), match.group(0)))
    return facets

def gen_link(start, end, uri):
    return {
        "index": {
            "byteStart": start,
            "byteEnd": end
        },
        "features": [{
            "$type": "app.bsky.richtext.facet#link",
            "uri": uri
        }]
    }



'''
fh = open("feeds.json", "r")
FEEDS = json.load(fh)
fh.close()
'''
print("Starting")
FEED_URL = os.getenv('FEED_URL', 'https://www.bentasker.co.uk/rss.xml')
HASH_DIR = os.getenv('HASH_DIR', '')
INCLUDE_AUTHOR = os.getenv('INCLUDE_AUTHOR', "True")
DRY_RUN = os.getenv('DRY_RUN', "N").upper()
SKIP_TAGS = os.getenv('SKIP_TAGS', "").lower().split(',')
TRACKING_MODE = os.getenv('TRACKING_MODE', "LASTPAGE").upper()

BSKY_USER = os.getenv('BSKY_USER', False)
BSKY_PASS = os.getenv('BSKY_PASS', "")

THREADS_USER = os.getenv('THREADS_USER', False)
THREADS_PASS = os.getenv('THREADS_PASS', "")

NOSTR_RELAYS = os.getenv('NOSTR_RELAYS', "").split(",")
NOSTR_PRIVATE_KEY = os.getenv('NOSTR_PK', False)

URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

DO_NOSTR = False
if NOSTR_PRIVATE_KEY:
    DO_NOSTR = True
    
    # Set up the relay connections
    NOSTR_RELAY = RelayManager()
    NOSTR_PK = PrivateKey.from_nsec(NOSTR_PRIVATE_KEY)
    
    for relay in NOSTR_RELAYS:
        NOSTR_RELAY.add_relay(relay)
    time.sleep(1.25)

if BSKY_USER:
    BSKY_CLIENT = Client()
    profile = BSKY_CLIENT.login(BSKY_USER, BSKY_PASS)


# We want to be able to use keep-alive if we're posting multiple things
SESSION = requests.session()


feed = {}
feed['FEED_URL'] = FEED_URL
feed['HASH_FILE'] = f"{HASH_DIR}/{hashlib.sha1(feed['FEED_URL'].encode('utf-8')).hexdigest()}"

feed['HASH_DIR'] = f"{feed['HASH_FILE']}.urls"
if not os.path.exists(feed['HASH_DIR']):
    os.makedirs(feed['HASH_DIR'])
    
for service in ["threads", "nostr", "bsky"]:       
    if not os.path.exists(f"{feed['HASH_DIR']}/{service}"):
        os.makedirs(f"{feed['HASH_DIR']}/{service}")


process_feed(feed)

if DO_NOSTR:
    # Make sure we allow time for messages to send
    time.sleep(1)
    NOSTR_RELAY.close_connections()
    
print("Finished")
