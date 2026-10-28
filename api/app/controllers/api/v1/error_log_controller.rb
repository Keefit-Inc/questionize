module Api
  module V1
    # The error log (docs/KNOWLEDGE_MODEL.md §9): one photographed question at a time.
    class ErrorLogController < BaseController
      MAX_IMAGE_BYTES = 6.megabytes
      IMAGE = %r{\Adata:image/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+\z}
      MAX_PARTS = 3

      rate_limit to: 10, within: 10.minutes, only: :create, by: -> { current_user.id }

      # GET /api/v1/error_log
      def index
        entries = current_user.error_log_entries.includes(:generation_run).order(created_at: :desc).limit(50).to_a
        render json: {
          eligible: current_user.error_log_eligible?,
          entries: entries.map { |entry| ErrorLogPayload.new(entry, user: current_user).as_json },
          weaknesses: ErrorLogPayload.weaknesses(entries)
        }
      end

      # GET /api/v1/error_log/:id
      def show
        entry = current_user.error_log_entries.find(params[:id])
        render json: ErrorLogPayload.new(entry, user: current_user).as_json
      end

      # GET /api/v1/error_log/:id/question
      # The photographed question, word for word, handed to the learner's device once: it is
      # kept only in the cache until then and deleted as it is read (docs/KNOWLEDGE_MODEL.md §9).
      def question
        entry = current_user.error_log_entries.find(params[:id])
        key = GenerationRuns::Recorder.question_cache_key(entry)
        question = Rails.cache.read(key)
        return render(json: { error: "not_available" }, status: :not_found) unless question

        Rails.cache.delete(key)
        render json: question
      end

      # POST /api/v1/error_log {images: [data URL, ...] (1-3 parts of one question), book, page, number, chosen_label}
      def create
        return render(json: { error: "not_available" }, status: :forbidden) unless current_user.error_log_eligible?

        images = Array(params[:images].presence || params[:image]).map(&:to_s)
        return render(json: { error: "invalid_image" }, status: :unprocessable_entity) unless images.size.between?(1, MAX_PARTS) && images.all? { valid_image?(_1) }
        label = params[:chosen_label].presence&.upcase
        return render(json: { error: "invalid_label" }, status: :unprocessable_entity) if label && !ItemVersion::LABELS.include?(label)

        run = GenerationRun.create!(
          user: current_user, kind: "error_log",
          params: { "book" => params[:book].to_s.strip.first(200), "page" => params[:page].to_s.strip.first(20),
                    "number" => params[:number].to_s.strip.first(20), "chosen_label" => label }
        )
        run.cache_text!(images.to_json)
        GenerateQuestionsJob.perform_later(run.id)
        render json: { status: "queued", run_id: run.id }, status: :accepted
      end

      private

      def valid_image?(image)
        image.bytesize <= MAX_IMAGE_BYTES * 4 / 3 && image.match?(IMAGE)
      end
    end
  end
end
