

# TODO:
stuff that needs to be done

### User
- store user information? (could probably just use sessions)

### Authentication:
- Add logic for refreshing token in auth.py

### Redis:
- Add retry logic (currently expects every transaction is sucessful)
- Add docstrings for each redis transaction
- Add decorator for logic regarding if access token exists on every set or get call 
(currently assumes access token is always exists, might want to redir authentication if access token
expired)
- Possibly turn this set of functions into a class? Only benefit right now is abstracting `access_token`
- Consider using hashes (md5) for redis keys
- dump redis rdb and use to open file
- set TTL for user values based on auth tokens expiry

### Formatting:
- Change all functions to underscore delimited from camel case
- Try to add typing to all parameters and functions

### Playlists Features
- Sort by popularity (p3)
- Play button (p1)
- Play respective playlist (queue all songs?) (p5)
##### Exporting
- Delete after exporting (in case it was an accident) (p3)
- exporting playlist (p1)
- allow user to name playlist (p1)

### Home Features 
- loading page (p2)
- increase size of bubbles to fit screen (p1)
- moving around song bubbles
- play around with treemap vs bubbles
- include data science perspective

### JS
- move to webpack from bower (deprecated)