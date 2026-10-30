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

    render json: Research::Feed.merge_scoreboard(JSON.parse(path.read))
  end

  def cycles
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Authorization"
    token = request.authorization.to_s[/\ABearer\s+(.+)\z/i, 1]
    user = User.find_by(api_token: token) if token.present?
    render json: Research::Feed.public_data(user: user)
  end

  def ledger
    response.headers["Cache-Control"] = "no-store"
    rows = Research::Cycle.where(status: Research::Cycle::TERMINAL).order(:id).filter_map { _1.ledger_entry.presence }
    render plain: rows.map(&:to_json).join("\n") + (rows.any? ? "\n" : ""), content_type: "application/x-ndjson"
  end
end
