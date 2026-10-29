# The public worker script is revalidated independently of the immutable hashed assets.
class ServiceWorkerController < ActionController::API
  def show
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    path = [ Rails.root.join("service-worker.js"), Rails.root.join("../web/public/sw.js") ].find(&:exist?)
    return head :not_found unless path

    render plain: path.read, content_type: "application/javascript"
  end
end
