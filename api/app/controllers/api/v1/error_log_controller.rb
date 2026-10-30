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

      # PATCH /api/v1/error_log/:id {archived: true|false}
      def update
        entry = current_user.error_log_entries.find(params[:id])
        entry.update!(archived_at: ActiveModel::Type::Boolean.new.cast(params[:archived]) ? (entry.archived_at || Time.current) : nil)
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

        Rails.cache.delete(key) unless params[:retain_until_saved] == "1"
        render json: question
      end

      def acknowledge_question
        entry = current_user.error_log_entries.find(params[:id])
        Rails.cache.delete(GenerationRuns::Recorder.question_cache_key(entry))
        head :no_content
      end

      # POST /api/v1/error_log {images: [data URL, ...] (1-3 parts of one question), book, page, number,
      #                        chosen_label, answer_key (from the book's key, optional and checked),
      #                        learn_only, dataset (curators only)}
      def create
        return render(json: { error: "not_available" }, status: :forbidden) unless current_user.error_log_eligible?

        images = Array(params[:images].presence || params[:image]).map(&:to_s)
        return render(json: { error: "invalid_image" }, status: :unprocessable_entity) unless images.size.between?(1, MAX_PARTS) && images.all? { valid_image?(_1) }
        label = params[:chosen_label].presence&.upcase
        key = params[:answer_key].presence&.upcase
        return render(json: { error: "invalid_label" }, status: :unprocessable_entity) if [ label, key ].compact.any? { !ItemVersion::LABELS.include?(_1) }
        # Learn-only captures and dataset tags are for curators building research datasets.
        learn_only = (current_user.curator && ActiveModel::Type::Boolean.new.cast(params[:learn_only])) || nil
        dataset = current_user.curator ? params[:dataset].to_s.downcase.strip.presence : nil
        return render(json: { error: "invalid_dataset" }, status: :unprocessable_entity) if dataset && !dataset.match?(/\A[a-z0-9][a-z0-9-]{0,39}\z/)

        run = GenerationRun.create!(
          user: current_user, kind: "error_log",
          params: { "book" => params[:book].to_s.strip.first(200), "page" => params[:page].to_s.strip.first(20),
                    "number" => params[:number].to_s.strip.first(20), "chosen_label" => label, "answer_key" => key,
                    "source_attested" => current_user.curator && key.present? && ActiveModel::Type::Boolean.new.cast(params[:source_attested]),
                    "operator_test" => Rails.cache.read("research/operator-test-user/#{current_user.id}") == true,
                    "learn_only" => learn_only, "dataset" => dataset, "level" => Level.for(current_user) }.compact
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
