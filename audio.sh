pip install elevenlabs python-dotenv

# List audio devices
aplay -l

# Find your USB speaker (e.g., card 1, device 0)
# Then set it as default by editing/creating ~/.asoundrc:
echo 'defaults.pcm.card 1
defaults.ctl.card 1' > ~/.asoundrc