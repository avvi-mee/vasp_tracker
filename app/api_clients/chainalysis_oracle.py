# Replaced by app/api_clients/chainalysis.py, which covers both of
# Chainalysis's free sanctions interfaces (the on-chain oracle that lives
# here originally, plus the Sanctions Screening API) rather than only the
# oracle the old filename named.
#
# Nothing imports this any more — verified by grep across app/ and tests/.
# It is left as an empty module only because the tooling that made this
# change could not delete a file. Safe to remove:
#
#     git rm app/api_clients/chainalysis_oracle.py
