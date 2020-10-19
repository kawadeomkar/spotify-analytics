

#TODO:
stuff that needs to be done


Authentication:
- Add logic for refreshing token in auth.py


Redis:
- Add retry logic (currently expects every transaction is sucessful)
- Add docstrings for each redis transaction
- Add decorator for logic regarding if access token exists on every set or get call 
(currently assumes access token is always exists, might want to redir authentication if access token
expired)
- Possibly turn this set of functions into a class? Only benefit right now is abstracting `access_token`