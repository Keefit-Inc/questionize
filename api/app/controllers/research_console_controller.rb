# A separate Vue entry point for the published aggregate research record.
# No private item text, per-item output, credentials or write operations are exposed here.
class ResearchConsoleController < ActionController::Base
  def show
    response.headers["Cache-Control"] = "no-cache"
    path = Rails.root.join("admin.html")
    return head :service_unavailable unless path.exist?

    render html: path.read.html_safe, layout: false # static build output, no user content
  end

  def data
    response.headers["Cache-Control"] = "no-store"
    path = Rails.root.join("research-dashboard.json")
    return head :service_unavailable unless path.exist?

    render plain: path.read, content_type: "application/json"
  end
end
