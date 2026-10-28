module Api
  module V1
    # A bank item on the learner's review list (My misses).
    class SavedItemsController < BaseController
      # PUT /api/v1/items/:item_id/save {archived: true|false}
      # Saves the item to practice later, or archives / restores it.
      def update
        item = Item.accessible_by(current_user).find_by!(public_id: params[:item_id])
        saved = Learning::SavedItem.find_by(user: current_user, item: item) || Learning::SavedItem.keep!(user: current_user, item: item, reason: "saved")
        saved.update!(archived_at: ActiveModel::Type::Boolean.new.cast(params[:archived]) ? (saved.archived_at || Time.current) : nil)
        render json: { reason: saved.reason, archived: saved.archived_at.present? }
      end

      # DELETE /api/v1/items/:item_id/save
      def destroy
        item = Item.accessible_by(current_user).find_by!(public_id: params[:item_id])
        Learning::SavedItem.where(user: current_user, item: item).delete_all
        head :no_content
      end
    end
  end
end
