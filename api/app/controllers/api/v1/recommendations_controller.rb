module Api
  module V1
    # GET /api/v1/recommendations — what to practice next (Learning::Recommend).
    class RecommendationsController < BaseController
      def index
        picks = Learning::Recommend.call(user: current_user, limit: params.fetch(:limit, 5).to_i.clamp(1, 20))
        render json: {
          level: Level.for(current_user),
          items: picks.map { |p| { reason: p.reason, item: ItemPayload.new(p.item, revealed: false, user: current_user).as_json } }
        }
      end
    end
  end
end
