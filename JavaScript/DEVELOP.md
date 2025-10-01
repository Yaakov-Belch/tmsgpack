```bash
# git clone git@github.com:Yaakov-Belch/tmsgpack.git
git clone https://github.com/Yaakov-Belch/tmsgpack.git

cd tmsgpack/JavaScript

# 1. Install and test
npm install
npm test

# 2. Log into npm
npm login
npm whoami

# 3. Dry run to verify package contents
npm pack                  # Creates tarball. No npm login needed
npm publish --dry-run     # Checks publication readiness.

# 4. Publish when ready
npm publish
```

