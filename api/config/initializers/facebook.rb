# Facebook Login. The app id is public (the web app loads it at runtime from /api/v1/config);
# the secret stays on the server and is used to verify tokens and data-deletion requests.
Rails.application.configure do
  config.x.facebook.app_id = ENV.fetch("FACEBOOK_APP_ID", "").presence
  config.x.facebook.app_secret = ENV.fetch("FACEBOOK_APP_SECRET", "").presence
  config.x.facebook.graph_url = ENV.fetch("FACEBOOK_GRAPH_URL", "https://graph.facebook.com/v21.0")
end
