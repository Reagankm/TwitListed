#!/usr/bin/env python
from __future__ import division
import tweepy, time, pprint, re
from flask import Flask, render_template, session, redirect, url_for, request
from datetime import datetime
import collections

#Create the application
app = Flask(__name__)

# TwitListed's API key and secret
# (copy-paste into code before running script)
# (Will find a better solution later)
consumer_key = 'fill with your info'
consumer_secret = 'fill with your info'

# TODO: If changing callback url here, remember to change callback at apps.twitter.com to new callback url
callback = "http://127.0.0.1:5000/callback"

# Secret key for the session
app.secret_key = 'fill with your info'

auth = tweepy.OAuthHandler(consumer_key, consumer_secret, callback)

@app.route('/')
def index():
    """ Displays the index page accessible at '/'"""
    return render_template('index.html')

# Fetch request token
# (Requests the token from twitter and returns the
# authorization url the user must visit in order
# to authorize this app)
@app.route('/auth')
def authorize():

    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepError:
        print 'Error! Failed to get request token.'

    # Store the request token in the session. (We will
    # need it inside the callback URL request)
    ## session.set('request_token', auth.request_token)
    session['request_token'] = auth.request_token
    return redirect(redirect_url)


# Exchange the request token for an access token
@app.route('/callback')
def twitter_callback():
    # Re-build the auth handler
    token = session['request_token']
    session.pop('request_token', None)
    auth.request_token = token
    verifier = request.args.get('oauth_verifier')
    
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        print 'Error! Failed to get access token.'

    return render_template('options.html')

sorted_friends = []





# Go through the accounts the user follows and calculate
# their average tweet frequency
@app.route('/frequency')
def frequency():
    # TODO: Add option to let people choose how they want frequency
    # calculated (default will be looking at from the last month
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    #Get accounts user follows
    user = api.me()

    friends_list = []
    Person = collections.namedtuple('Person', 'id name frequency color')
    #If user has under 3000 friends, proceed as usual
    if user.friends_count <= 3000:
        #For testing
        count = 0
        for friend in tweepy.Cursor(api.friends, count = 200).items():
#            current = {
#                "id": friend.id,
#                "name": friend.name,
                #"frequency": calc_frequency(friend, api) 
#                "frequency": get_tweet_freq(friend, api)
#                }
            freq = get_tweet_freq(friend, api)
            cell_color = get_color(freq)
            current = Person(id = friend.id,
                             name = friend.name,
                             frequency = freq,
                             color = cell_color)
            friends_list.append( current )
            #count += 1
            #if count > 50:
            #    break
        
    #else:
        
    #If they have more than 3000 friends, Twitter limits mean we have
    #to calculate this a different way
    #TO DO: Add warning label on html for users with over 3000 followers
            
    
    
    #Print them to the user in order of frequency
    #sorted_list = sorted(friends_list, key=lambda friends: friends[2])
    friends_list.sort(key=lambda x:x.frequency, reverse=True)
    global sorted_friends
    sorted_friends = friends_list #save in more global variable so it can be used elsewhere
    return render_template('frequency.html', accounts=friends_list)

def get_color(frequency):
    if frequency < 1:
        return "#7FFFD4" #aquamarine
    elif frequency < 5:
        return "#7FFF00" #chartreuse
    elif frequency < 30:
        return "#BA55D3" #medium orchid
#    elif frequency < 50:
#        return "#FFFF00" #yellow
    else:
        return "#FF6347" #tomato

#Returns true if the first character of the tweet is not an @ symbol,
#otherwise returns false
def at_free(text):
    return text[0] != '@'

# Looks at the last 100 tweets and returns the avg # tweets per day
def get_tweet_freq(account, api):
    try:
        tweets = api.user_timeline(user_id = account.id, count=200, include_rts=1, include_entities=1, page=1)
    except tweepy.error.TweepError:
        time.sleep(30)
        tweets = api.user_timeline(user_id = account.id, count=200, exclude_replies=1, include_rts=1, page=1)

    #Remove any tweets that start with "@" by default
    tweets[:] = [x for x in tweets if at_free(x.text)]
            
        
    length = len(tweets)
    if length > 0:
        
        #oldest_tweet = tweets[-1]
        index = 0
        oldest_tweet = tweets[0]
        while index != length:
            
            challenger = tweets[index]
            #if account.name == "AnthroPunk":
            #    print str(index) + " => " + challenger.text
            oldest_tweet = challenger if (challenger.created_at < oldest_tweet.created_at) else oldest_tweet
            index += 1
            
        days_since_oldest = (datetime.now() - oldest_tweet.created_at).days
        #print account.name + "'s oldest tweet: " + oldest_tweet.text
        if days_since_oldest == 0:
            return length
        else:
            return length / days_since_oldest
    else:
        return 0
        
# Returns how many tweets the user sent since a given date
def get_tweet_count(start_date, account, api):
    
    #Get tweets
    is_done = False
    page = 0
    total_tweets = 0

    while not is_done:
        tweets = []
        try:
            page += 1
            tweets = api.user_timeline(user_id = account.id, count=200, include_rts=1, include_entities=1, page=page)
        except tweepy.error.TweepError:
            print "TWEEPY ERROR. Trying again in 30 seconds"
            time.sleep(30) #to resolve error with Twitter API rate limit
            tweets = api.user_timeline(user_id = account.id, count=200, include_rts=1, include_entities=1, page=page)

        length = len(tweets)
        tweets_in_range = 0
        if length > 0:
            #Find out how many of these tweets are within our date range
            tweets_in_range = binary_search_for_date(tweets, start_date)
            total_tweets += tweets_in_range
        if tweets_in_range < 200:
            #Unless every tweet from the current list is still within range,
            #we have reached the end of the tweets in range
            is_done = True
    return total_tweets

#Accepts a Twitter account and calculates its average
#tweets per day
def calc_frequency(account, api):
    #Get farthest back tweet date to use when averaging
    date_string = "08/28/2015"
    date_list = date_string.split('/')
    start_date = datetime(int(date_list[2]), int(date_list[0]), int(date_list[1]))
    
    days_since_start = (datetime.now() - start_date).days

    count = get_tweet_count(start_date, account, api)

    return count / days_since_start
    
# Searches through a list of tweets and returns how many are at least as
# old as the supplied "oldest date"
def binary_search_for_date(tweet_list, oldest_date):
    first = 0
    last = len(tweet_list)-1
    oldest_index = -1
    while first <= last:
        midpoint = (first + last) // 2
        current = tweet_list[midpoint]
        #date_diff = oldest_date - current.created_at
        #if date_diff.total_seconds() >= 0: #Still a valid date
        if current.created_at >= oldest_date:
            first = midpoint + 1
            oldest_index = midpoint
                
        else:
            last = midpoint - 1
    return oldest_index + 1
    

#Create lists as calculated
@app.route('/create_lists')
def create_lists():
    rare_name = "TwitListed: Tweet Rarely"
    low_name = "TwitListed: Tweet A Bit"
    mid_name = "TwitListed: Tweet Often"
#    high_name = "Tweet Frequency Between 30 and 50 per Day"
    highest_name = "TwitListed: Tweet So Much"

    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    #Create the lists and then get their "slug" id
    rare_slug = api.create_list(name=rare_name, mode="private", description="Accounts who tweet, on average, less often than once per day. Created by TwitListed.").slug
    low_slug = api.create_list(name=low_name, mode="private", description="Accounts who tweet, on average, between 1 and fewer than 5 times per day. Created by TwitListed.").slug
    mid_slug = api.create_list(name=mid_name, mode="private", description="Accounts who tweet, on average, between 5 and fewer than 30 times per day. Created by TwitListed.").slug
#    api.create_list(name=high_name, description="Stores accounts who tweet, on average, between 30 and less than 50 times per day. Created by TwitListed.")
    highest_slug = api.create_list(name=highest_name, mode="private", description="Accounts who tweet, on average, 50 or more times per day. Created by TwitListed.").slug

#    list_of_lists = api.lists()
#    rare_slug = ""
#    low_slug = ""
#    mid_slug = ""
#    high_slug = ""
#    highest_slug = ""
    
#    for item in list_of_lists:
 #       if item.name == rare_name:
  #          rare_slug = item.slug
   #     elif item.name == low_name:
    #        low_slug = item.slug
     #   elif item.name == mid_name:
      #      mid_slug = item.slug
 #       elif item.name == high_name:
 #           high_slug = item.slug
 #       elif item.name == highest_name:
  #          highest_slug = item.slug
   #     else:
    #        a = True #No action needed

    owner = api.me()
    
    print "Sorted Friends have length " + str(len(sorted_friends))
    for acct in sorted_friends:
        frequency = acct.frequency
        
        if frequency < 1: #rare
            #print "rare"
            api.add_list_member(slug=rare_slug, user_id=acct.id, owner_id=owner.id)
        elif frequency < 5: #low
            #print "low"
            api.add_list_member(slug=low_slug, id=acct.id, owner_id=owner.id)
        elif frequency < 30: #mid
            #print "mid"
            api.add_list_member(slug=mid_slug, id=acct.id, owner_id=owner.id)
#        elif frequency < 50: #high
#            api.add_list_member(slug=high_slug, id=acct.id)
        else: #highest
            #print "high"
            api.add_list_member(slug=highest_slug, id=acct.id, owner_id=owner.id)

    return render_template('created.html', user=owner.screen_name)


if __name__ == '__main__':
    app.debug = True
    app.run()
