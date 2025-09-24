from flask import Flask, render_template_string, request, Response
import requests, datetime
from urllib.parse import quote, unquote

app = Flask(__name__)

@app.template_filter('url_encode')
def url_encode_filter(s):
    return quote(s, safe='')

@app.route("/", methods=["GET", "POST"])
def home():
    profile_data = None
    posts = []
    summary = {}
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        if username:
            url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
            headers = {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "x-ig-app-id": "936619743392459",
            }

            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    user = data.get("data", {}).get("user", {})

                    if user:
                        profile_data = {
                            "username": user.get("username", "N/A"),
                            "full_name": user.get("full_name", "N/A"),
                            "biography": user.get("biography", "N/A"),
                            "followers": user.get("edge_followed_by", {}).get("count", 0),
                            "following": user.get("edge_follow", {}).get("count", 0),
                            "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
                            "is_verified": user.get("is_verified", False),
                            "is_private": user.get("is_private", False),
                            "category": user.get("category_name", "N/A"),
                            "website": user.get("external_url", "N/A"),
                            "email": user.get("business_email", "N/A"),
                            "phone": user.get("business_phone_number", "N/A"),
                            "profile_pic_url": user.get("profile_pic_url_hd", "")
                        }

                        edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
                        total_likes = 0
                        total_comments = 0

                        for edge in edges:
                            node = edge.get("node", {})
                            image_url = node.get("display_url") or node.get("thumbnail_src", "")
                            if not image_url and node.get("thumbnail_resources"):
                                image_url = node["thumbnail_resources"][-1].get("src", "")

                            caption = ""
                            if node.get("edge_media_to_caption", {}).get("edges"):
                                caption = node["edge_media_to_caption"]["edges"][0]["node"].get("text", "")

                            likes = node.get("edge_liked_by", {}).get("count", 0)
                            comments = node.get("edge_media_to_comment", {}).get("count", 0)
                            total_likes += likes
                            total_comments += comments

                            followers = max(profile_data['followers'], 1)
                            engagement_rate_post = round((likes + comments) / followers * 100, 2)

                            posts.append({
                                "thumbnail": image_url,
                                "caption": caption,
                                "likes": likes,
                                "comments": comments,
                                "timestamp": datetime.datetime.fromtimestamp(node.get("taken_at_timestamp", 0)).strftime("%b %d, %Y"),
                                "shortcode": node.get("shortcode", ""),
                                "engagement_rate": engagement_rate_post
                            })

                        num_posts = len(posts) if posts else 1
                        summary = {
                            "avg_likes": int(total_likes / num_posts),
                            "avg_comments": int(total_comments / num_posts),
                            "engagement_rate": round(((total_likes + total_comments) / max(profile_data['followers'], 1)) * 100, 2)
                        }

                    else:
                        error = "User not found!"
                else:
                    error = f"Error: {response.status_code}"
            except Exception as e:
                error = f"Request failed: {e}"

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Instagram Analytics Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

body {
  background: #121212;
  color: #e0e0e0;
  font-family: 'Inter', sans-serif;
  line-height: 1.6;
}
a {
  color: #3b82f6;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
h2, h4, h6 {
  color: #ffffff;
}
.card {
  border-radius: 12px;
  background: #1e1e1e;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
}
.profile-pic {
  border-radius: 50%;
  width: 120px;
  height: 120px;
  object-fit: cover;
  border: 3px solid #444;
}
.stats-card {
  text-align: center;
  padding: 15px;
  border-radius: 12px;
  background: #2a2a2a;
  transition: 0.3s;
}
.stats-card:hover {
  background: #3a3a3a;
  transform: translateY(-3px);
}
.stats-card h6 {
  margin: 0;
  font-weight: 600;
  font-size: 1.1rem;
  color: #fff;
}
.stats-card small {
  color: #bbb;
  font-size: 0.8rem;
}
.post-card {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  cursor: pointer;
}
.post-card img {
  width: 100%;
  height: 180px;
  object-fit: cover;
  transition: 0.3s;
}
.post-card:hover img {
  transform: scale(1.05);
}
.post-overlay {
  position: absolute;
  bottom: 0;
  width: 100%;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.7);
  font-size: 0.75rem;
  display: flex;
  justify-content: space-between;
  color: #fff;
  backdrop-filter: blur(4px);
}
.form-control {
  background: #2a2a2a;
  color: #e0e0e0;
  border: none;
}
.form-control::placeholder {
  color: #888;
}
.btn-primary {
  background: #3b82f6;
  border: none;
  font-weight: 500;
}
.alert {
  background: #2a2a2a;
  color: #e0e0e0;
  border: none;
}
</style>
</head>
<body>
<div class="container py-4">
<h2 class="text-center mb-4 fw-bold">Instagram Analytics Dashboard</h2>
<form method="POST" class="d-flex justify-content-center mb-4">
<input type="text" name="username" class="form-control w-50" placeholder="Enter Instagram username" required>
<button class="btn btn-primary ms-2"><i class="fa-solid fa-magnifying-glass"></i> Search</button>
</form>

{% if error %}
<div class="alert text-center">{{ error }}</div>
{% endif %}

{% if profile %}
<div class="d-flex flex-column flex-md-row align-items-center mb-4">
<img src="/proxy/{{ profile['profile_pic_url'] | url_encode }}" class="profile-pic me-md-4 mb-3 mb-md-0">
<div>
<h4>{{ profile['full_name'] }} {% if profile['is_verified'] %}<i class="fa-solid fa-circle-check text-primary"></i>{% endif %}</h4>
<h6 class="text-muted">@{{ profile['username'] }}</h6>
<p style="font-size:0.85rem; color:#ccc;">{{ profile['biography'] }}</p>
<p style="font-size:0.8rem;">
<i class="fa-solid fa-lock"></i> {% if profile['is_private'] %} Private {% else %} Public {% endif %} |
<i class="fa-solid fa-briefcase"></i> {{ profile['category'] }}
</p>
{% if profile['website'] != "N/A" %}<p style="font-size:0.8rem;"><i class="fa-solid fa-link"></i> <a href="{{ profile['website'] }}" target="_blank">{{ profile['website'] }}</a></p>{% endif %}
</div>
</div>

<div class="row mb-4 g-3 justify-content-center">
<div class="col-6 col-md-2"><div class="stats-card"><i class="fa-solid fa-camera fa-lg mb-1"></i><h6>{{ profile['posts'] }}</h6><small>Posts</small></div></div>
<div class="col-6 col-md-2"><div class="stats-card"><i class="fa-solid fa-users fa-lg mb-1"></i><h6>{{ profile['followers'] }}</h6><small>Followers</small></div></div>
<div class="col-6 col-md-2"><div class="stats-card"><i class="fa-solid fa-user-plus fa-lg mb-1"></i><h6>{{ profile['following'] }}</h6><small>Following</small></div></div>
<div class="col-6 col-md-2"><div class="stats-card"><i class="fa-solid fa-heart fa-lg text-danger mb-1"></i><h6>{{ summary['avg_likes'] }}</h6><small>Avg Likes</small></div></div>
<div class="col-6 col-md-2"><div class="stats-card"><i class="fa-solid fa-comment fa-lg text-primary mb-1"></i><h6>{{ summary['avg_comments'] }}</h6><small>Avg Comments</small></div></div>
<div class="col-6 col-md-2"><div class="stats-card"><i class="fa-solid fa-chart-line fa-lg text-success mb-1"></i><h6>{{ summary['engagement_rate'] }}%</h6><small>Engagement</small></div></div>
</div>

{% if posts %}
<div class="row g-3 mb-4">
<div class="col-md-6">
<div class="card p-3">
<h6 class="mb-2 text-light">Likes & Comments Trend</h6>
<canvas id="trendChart"></canvas>
</div>
</div>
<div class="col-md-6">
<div class="card p-3">
<h6 class="mb-2 text-light">Engagement Rate per Post (%)</h6>
<canvas id="engagementChart"></canvas>
</div>
</div>
</div>

<h6 class="mb-3 text-center text-light">Recent Posts</h6>
<div class="row g-3">
{% for post in posts %}
<div class="col-6 col-md-3">
<div class="post-card">
<a href="https://www.instagram.com/p/{{ post['shortcode'] }}/" target="_blank">
<img src="/proxy/{{ post['thumbnail'] | url_encode }}" onerror="this.onerror=null;this.src='https://via.placeholder.com/400x400?text=No+Image';">
<div class="post-overlay">
<span><i class="fa-solid fa-heart text-danger"></i> {{ post['likes'] }}</span>
<span><i class="fa-solid fa-comment text-primary"></i> {{ post['comments'] }}</span>
<span>{{ post['timestamp'] }}</span>
</div>
</a>
</div>
</div>
{% endfor %}
</div>

<script>
const labels = [{% for post in posts %}'Post {{ loop.index }}',{% endfor %}];
const likesData = [{% for post in posts %}{{ post['likes'] }},{% endfor %}];
const commentsData = [{% for post in posts %}{{ post['comments'] }},{% endfor %}];
const engagementData = [{% for post in posts %}{{ post['engagement_rate'] }},{% endfor %}];

new Chart(document.getElementById('trendChart').getContext('2d'), {
type:'line',
data:{
labels:labels,
datasets:[
{label:'Likes', data:likesData, borderColor:'rgba(255,99,132,1)', backgroundColor:'rgba(255,99,132,0.2)', tension:0.3, fill:false, pointRadius:4},
{label:'Comments', data:commentsData, borderColor:'rgba(54,162,235,1)', backgroundColor:'rgba(54,162,235,0.2)', tension:0.3, fill:false, pointRadius:4}
]
},
options:{
responsive:true,
plugins:{legend:{position:'top', labels:{color:'#e0e0e0'}}},
interaction:{mode:'index', intersect:false},
scales:{
x:{title:{display:true,text:'Posts', color:'#e0e0e0'}, ticks:{color:'#e0e0e0'}},
y:{title:{display:true,text:'Count', color:'#e0e0e0'}, ticks:{color:'#e0e0e0'}}
}
}
});

new Chart(document.getElementById('engagementChart').getContext('2d'), {
type:'bar',
data:{
labels:labels,
datasets:[{label:'Engagement Rate (%)', data:engagementData, backgroundColor:'rgba(75,192,192,0.6)'}]
},
options:{
responsive:true,
plugins:{legend:{display:true, labels:{color:'#e0e0e0'}}},
scales:{
y:{beginAtZero:true, title:{display:true,text:'Engagement Rate (%)', color:'#e0e0e0'}, ticks:{color:'#e0e0e0'}},
x:{ticks:{color:'#e0e0e0'}}
}
}
});
</script>
{% endif %}
{% endif %}
</div>
</body>
</html>
"""
    return render_template_string(html, profile=profile_data, posts=posts, summary=summary, error=error)

@app.route("/proxy/<path:url>")
def proxy(url):
    try:
        real_url = unquote(url)
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.instagram.com/",
            "cookie": "sessionid=PASTE_YOUR_SESSION_ID_HERE"
        }
        resp = requests.get(real_url, headers=headers, stream=True, timeout=10)
        resp.raise_for_status()
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return f"Proxy error: {e}", 500

import os
# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # fallback to 10000 locally
    app.run(host='0.0.0.0', port=port)
