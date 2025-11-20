# Debug Output Instructions

## What I Added

I've added detailed debug output that shows **exactly** what's happening at each step:

### In CLI (`src/cli.py`):
- Step 1: Creating directory
- Step 2: Initializing content generator
- Step 3: Calling API (with time expectation)
- Step 4: Saving files
- Full error tracebacks if something fails

### In Content Generator (`src/content_generator.py`):
- Provider selection
- Prompt building
- API configuration
- Request sending
- Response receiving
- Parsing

## Run with Debug Output

```bash
./pocket-guide-nofilter generate \
  --city "Rome" \
  --poi "Colosseum" \
  --provider openai \
  --description "Test"
```

## What You Should See

```
Step 1: Creating directory structure...
✓ Directory created: /path/to/content/rome/colosseum

Step 2: Initializing openai content generator...
Step 3: Calling openai API to generate content...
   (This usually takes 10-30 seconds)
  [DEBUG] Using provider: openai
  [DEBUG] Building prompt for Colosseum...
  [DEBUG] Prompt built (1234 chars)
  [DEBUG] Calling openai API...
  [DEBUG] Configuring OpenAI...
  [DEBUG] Model: gpt-4-turbo-preview
  [DEBUG] API key present: True
  [DEBUG] Prompt length: 1234 chars, System prompt: 567 chars
  [DEBUG] Creating OpenAI client and sending request...

  <<<<< IF IT HANGS, IT WILL BE HERE >>>>>

  [DEBUG] Response received! Length: 890 chars
  [DEBUG] Parsing response...
  [DEBUG] Parsing complete
✓ Content received from API

Step 4: Saving content to files...
✓ Files saved

✓ Content generated successfully!
...
```

## Where It's Likely Hanging

If it stops at **"Creating OpenAI client and sending request..."**, the issue is:

1. **API Key Invalid** - OpenAI is rejecting your key
2. **Network Issue** - Can't reach OpenAI servers
3. **Rate Limit** - You've hit API rate limits
4. **Timeout** - API is taking too long (I added 60s timeout)

## Quick Test Now

```bash
# Test with a simple request
./pocket-guide-nofilter generate \
  --city "Test" \
  --poi "Test" \
  --provider openai \
  --description "A test"
```

Watch for where it stops. The debug output will tell you **exactly** where.

## Interpreting the Output

| What You See | What It Means |
|--------------|---------------|
| Stops at "Creating directory" | File system issue |
| Stops at "Building prompt" | Config parsing issue |
| Stops at "Configuring OpenAI" | Provider config issue |
| Stops at "Creating OpenAI client" | **API key or network issue** |
| Stops after "sending request" | **Waiting for API (normal up to 60s)** |
| Shows "Response received" | API worked! Issue is parsing |

## If It Times Out After 60s

```
Error: Timeout after 60 seconds
```

This means:
- OpenAI API is down or slow
- Your network is blocking the request
- Your API key has rate limits

**Try:**
1. Check OpenAI status: https://status.openai.com/
2. Try a different provider: `--provider anthropic` or `--provider google`
3. Check your API key in config.yaml

## Next Steps

Run the command and **copy the full output** (all the debug lines). This will show us exactly where it's hanging!
