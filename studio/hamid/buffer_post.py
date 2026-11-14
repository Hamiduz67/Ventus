"""Schedule a finished video on YouTube Shorts + TikTok + Instagram Reels through Buffer's free plan.
(Facebook is covered by Instagram's own "share Reels to Facebook" setting.)

Usage:
  buffer_post.py schedule --url <public mp4 url> --caption "<text>" --title "<YouTube title>" \
                          --tiktok-title "<short title>" --at "2026-11-15 13:00" [--channels youtube,tiktok,instagram]
  buffer_post.py status   [--since-hours 24]      # list recent posts and their status
Key: env BUFFER_API_KEY, else ~/.secrets/buffer_key. Never commit the key (the repo is public)."""
import argparse, datetime as dt, json, os, subprocess, sys

KEY = os.environ.get("BUFFER_API_KEY") or open(os.path.expanduser("~/.secrets/buffer_key")).read().strip()
ORG = "6af7ea36a17764d6a490fc9f"
CHANNELS = {"tiktok": "6af7eb8162b70b94b0276170", "youtube": "6af7eb0862b70b94b0274f19", "instagram": "6af7ead262b70b94b027458d"}
DUBAI = dt.timezone(dt.timedelta(hours=4))

def gql(query, variables=None):
    r = subprocess.run(["curl", "-sS", "-m", "180", "https://api.buffer.com", "-H", "Authorization: Bearer " + KEY,
                        "-H", "Content-Type: application/json", "-d", json.dumps({"query": query, "variables": variables or {}})],
                       capture_output=True, text=True)
    out = json.loads(r.stdout)
    if out.get("errors"): print("GraphQL errors:", json.dumps(out["errors"])[:800]); sys.exit(1)
    return out["data"]

CREATE = """mutation C($input: CreatePostInput!) { createPost(input: $input) {
  ... on PostActionSuccess { post { id status dueAt channelId } } ... on MutationError { message } } }"""

def schedule(a):
    due = dt.datetime.strptime(a.at, "%Y-%m-%d %H:%M").replace(tzinfo=DUBAI).astimezone(dt.timezone.utc)
    if due < dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=3):
        print("ERROR: post time is in the past or too close:", a.at); sys.exit(1)
    meta = {"youtube": {"youtube": {"title": a.title[:100], "privacy": "public", "categoryId": "1", "madeForKids": False,
                                    "isAiGenerated": False, "notifySubscribers": True}},
            "tiktok": {"tiktok": {"title": (a.tiktok_title or a.title)[:90], "isAiGenerated": True}},
            "instagram": {"instagram": {"type": "reel", "shouldShareToFeed": True, "isAiGenerated": True}}}
    ok = True
    for svc in a.channels.split(","):
        inp = {"channelId": CHANNELS[svc], "text": a.caption, "assets": [{"video": {"url": a.url}}], "metadata": meta[svc],
               "schedulingType": "automatic", "mode": "customScheduled", "dueAt": due.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "needsApproval": False}
        res = gql(CREATE, {"input": inp})["createPost"]
        if "post" in res: print(svc, "scheduled", res["post"]["id"], res["post"]["status"], res["post"]["dueAt"])
        else: print(svc, "FAILED:", res.get("message")); ok = False
    sys.exit(0 if ok else 2)

def status(a):
    q = """query P($input: PostsInput!) { posts(input: $input, first: 30) { edges { node {
             id status dueAt sentAt channelId text error { message } } } } }"""
    try:
        d = gql(q, {"input": {"organizationId": ORG, "filter": {"channelIds": list(CHANNELS.values())}}})
    except SystemExit:
        d = gql(q, {"input": {"organizationId": ORG}})
    inv = {v: k for k, v in CHANNELS.items()}
    for e in d["posts"]["edges"]:
        n = e["node"]; err = (n.get("error") or {}).get("message", "")
        print(inv.get(n["channelId"], n["channelId"]), n["status"], n.get("dueAt"), n.get("sentAt"), (n.get("text") or "")[:50].replace("\n", " "), err)

p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("schedule"); s.add_argument("--url", required=True); s.add_argument("--caption", required=True)
s.add_argument("--title", required=True); s.add_argument("--tiktok-title"); s.add_argument("--at", required=True)
s.add_argument("--channels", default="youtube,tiktok,instagram")
st = sub.add_parser("status"); st.add_argument("--since-hours", type=int, default=24)
a = p.parse_args(); schedule(a) if a.cmd == "schedule" else status(a)
