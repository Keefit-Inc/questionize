module Api
  module V1
    # GET /api/v1/review?archived=true
    # The learner's review list, newest first: questions they snapped and bank items they missed
    # or saved. With archived=true, the ones they've moved out of the way.
    class ReviewController < BaseController
      LIMIT = 100

      def index
        archived = ActiveModel::Type::Boolean.new.cast(params[:archived])
        entries = current_user.error_log_entries.includes(:generation_run).then { archived ? _1.archived : _1.active }.order(created_at: :desc).limit(LIMIT)
        saved = current_user.saved_items.includes(item: %i[current_version source]).then { archived ? _1.archived : _1.active }.order(updated_at: :desc).limit(LIMIT)
        attempted = Learning::Attempt.where(user: current_user, item_id: saved.map(&:item_id)).distinct.pluck(:item_id).to_set

        cards = entries.map { |e| { kind: "snap", at: e.created_at, entry: ErrorLogPayload.new(e, user: current_user).as_json } } +
                saved.map do |s|
                  { kind: "item", at: s.updated_at, reason: s.reason,
                    item: ItemPayload.new(s.item, revealed: attempted.include?(s.item_id), user: current_user).as_json }
                end
        render json: { cards: cards.sort_by { -_1[:at].to_f }.first(LIMIT) }
      end
    end
  end
end
