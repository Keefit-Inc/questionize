module Api
  module V1
    # The error log (docs/KNOWLEDGE_MODEL.md §9): one photographed question at a time.
    class ErrorLogController < BaseController
      MAX_IMAGE_BYTES = 6.megabytes
      IMAGE = %r{\Adata:image/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+\z}

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

      # POST /api/v1/error_log {image, book, page, number, chosen_label}
      def create
        return render(json: { error: "not_available" }, status: :forbidden) unless current_user.error_log_eligible?

        image = params.require(:image).to_s
        return render(json: { error: "invalid_image" }, status: :unprocessable_entity) unless image.bytesize <= MAX_IMAGE_BYTES * 4 / 3 && image.match?(IMAGE)
        label = params[:chosen_label].presence&.upcase
        return render(json: { error: "invalid_label" }, status: :unprocessable_entity) if label && !ItemVersion::LABELS.include?(label)

        run = GenerationRun.create!(
          user: current_user, kind: "error_log",
          params: { "book" => params[:book].to_s.strip.first(200), "page" => params[:page].to_s.strip.first(20),
                    "number" => params[:number].to_s.strip.first(20), "chosen_label" => label }
        )
        run.cache_text!(image)
        GenerateQuestionsJob.perform_later(run.id)
        render json: { status: "queued", run_id: run.id }, status: :accepted
      end
    end
  end
end
