module Api
  module V1
    # Map → Challenge: the argument's structure, the judge's measurements and critical questions.
    class MapsController < BaseController
      rate_limit to: 5, within: 1.minute, only: :create, by: -> { current_user.id }

      # POST /api/v1/maps {url, title, text, selection}
      # A source's completed map is shared by every reader (200); otherwise a run starts (202).
      def create
        attrs = params.permit(:url, :title, :text, :selection)
        return render(json: { error: "article_too_short" }, status: :unprocessable_entity) if attrs[:text].to_s.length < 200
        return render(json: { error: "daily_limit_reached" }, status: :too_many_requests) if over_daily_limit?

        source = Source.for_page!(url: attrs[:url], title: attrs[:title], text: attrs[:text])
        if (existing = GenerationRun.completed_maps.where(source: source).order(:created_at).last)
          return render json: { status: "cached", map: MapPayload.new(existing, user: current_user).as_json }
        end

        run = GenerationRun.create!(user: current_user, source: source, kind: "map",
                                    params: { "url" => attrs[:url], "title" => attrs[:title].to_s, "selection" => attrs[:selection].to_s })
        run.cache_text!(attrs[:text])
        GenerateQuestionsJob.perform_later(run.id)
        render json: { status: "queued", run_id: run.id }, status: :accepted
      rescue URI::InvalidURIError
        render json: { error: "invalid_url" }, status: :unprocessable_entity
      end

      # GET /api/v1/maps/:id
      def show
        render json: MapPayload.new(find_map, user: current_user).as_json
      end

      private

      def find_map
        GenerationRun.completed_maps.find(params[:id])
      end

      def over_daily_limit?
        GenerationRun.where(user: current_user, created_at: Time.current.all_day).count >= GenerationsController::DAILY_LIMIT
      end
    end
  end
end
