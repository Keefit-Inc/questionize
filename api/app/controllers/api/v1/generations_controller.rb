module Api
  module V1
    class GenerationsController < BaseController
      DAILY_LIMIT = 30
      FAMILIES = %w[CR RC SC].freeze

      rate_limit to: 5, within: 1.minute, only: :create, by: -> { current_user.id }

      # POST /api/v1/generations
      # Returns verified items for the source if the bank already has them (200);
      # otherwise starts a run whose progress streams on GenerationChannel (202).
      def create
        attrs = generation_params
        return render(json: { error: "article_too_short" }, status: :unprocessable_entity) if attrs[:text].to_s.length < 200
        return render(json: { error: "daily_limit_reached" }, status: :too_many_requests) if over_daily_limit?

        source = Source.for_page!(url: attrs[:url], title: attrs[:title], text: attrs[:text])
        existing = source.items.where(status: "verified", level: Level.for(current_user)).includes(:current_version, :source).order(:created_at)
        if existing.any?
          return render json: { status: "cached", items: existing.map { |item| ItemPayload.for(item, user: current_user).as_json } }
        end

        run = GenerationRun.create!(user: current_user, source: source, params: run_params(attrs))
        run.cache_text!(attrs[:text])
        GenerateQuestionsJob.perform_later(run.id)
        render json: { status: "queued", run_id: run.id }, status: :accepted
      rescue URI::InvalidURIError
        render json: { error: "invalid_url" }, status: :unprocessable_entity
      end

      # GET /api/v1/generations/:id — catch up after reconnecting.
      def show
        run = current_user_runs.find(params[:id])
        render json: {
          run_id: run.id, status: run.status, events: run.events,
          items: run.items.includes(:current_version, :source).map { |item| ItemPayload.for(item, user: current_user).as_json }
        }
      end

      private

      def current_user_runs
        GenerationRun.where(user: current_user)
      end

      def generation_params
        params.permit(:url, :title, :text, :selection, :difficulty, :count_per_type, types: [])
      end

      def run_params(attrs)
        {
          "url" => attrs[:url], "title" => attrs[:title].to_s, "selection" => attrs[:selection].to_s,
          "types" => (Array(attrs[:types]) & FAMILIES).presence || %w[CR RC],
          "difficulty" => Item::START_RATINGS.key?(attrs[:difficulty]) ? attrs[:difficulty] : "medium",
          "count_per_type" => attrs[:count_per_type].to_i.clamp(1, 3),
          "level" => Level.for(current_user)
        }
      end

      def over_daily_limit?
        current_user_runs.where(created_at: Time.current.all_day).count >= DAILY_LIMIT
      end
    end
  end
end
