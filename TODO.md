

# TODO:
stuff that needs to be done

### User
- store user information? (could probably just use sessions)

### Authentication:
- Add logic for refreshing token in auth.py (p2)

### Redis:
- Add retry logic (currently expects every transaction is sucessful)
- Add docstrings for each redis transaction
- Add decorator for logic regarding if access token exists on every set or get call 
(currently assumes access token is always exists, might want to redir authentication if access token
expired)
- Possibly turn this set of functions into a class? Only benefit right now is abstracting `access_token`
- Consider using hashes (md5) for redis keys (p2)
- ~~dump redis rdb snapshot for restoring redis instance (p2)~~ (10/30)
- set TTL for user values based on auth tokens expiry

### Formatting:
- Change all functions to underscore delimited from camel case (p3)
- Try to add typing to all parameters and functions (p5)

### Playlists Features
- Sort by popularity (p3)
- Play button (p1)
- Play respective playlist (queue all songs?) (p5)
- spotify web playback on browser (if no devices are found)
##### Exporting
- Delete after exporting (in case it was an accident) (p3)
- ~~exporting playlist (p1)~~ (10/29/2020)
- allow user to name playlist (p1)

### Home Features 
- loading page (p2)
- ~~increase size of bubbles to fit screen (p1)~~ (10/31/2020) 
- moving around song bubbles (p4)
- play around with treemap vs bubbles (p3)
- include data science perspective (p2)
- Automatic text resizing

### JS
- move to webpack from bower (deprecated) (p3)

### Styling
- fix genre title sizing on bubble (p2)
- make home page look better, more statistics
- improve styling of home page (p3)
- improve styling of playlist
- improve styling of export button
- add certain track pictures to playlist viewing

### Analytics
- trend of genre over time
- trend of songs added over time
- trend of certain artists
- treemap of genre broken down by artist 
- users top artists and tracks