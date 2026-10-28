module Api
  module V1
    class ItemsController < BaseController
      # GET /api/v1/items/:id (public id). Hidden fields appear once the user has attempted it.
      def show
        render json: ItemPayload.for(find_item, user: current_user).as_json
      end

      private

      def find_item
        Item.includes(:current_version, :source).find_by!(public_id: params[:id])
      end
    end
  end
end
