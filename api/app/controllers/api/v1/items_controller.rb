module Api
  module V1
    class ItemsController < BaseController
      PAGE_SIZE = 20

      # GET /api/v1/items?family=CR&level=middle&before=<public id> — the public feed, newest first.
      def index
        items = Item.listed.includes(:current_version, :source).order(published_at: :desc, id: :desc)
        items = items.where(family: params[:family]) if Item::FAMILIES.include?(params[:family])
        items = items.where(level: params[:level]) if Level.valid?(params[:level])
        if (cursor = params[:before].presence && Item.listed.find_by(public_id: params[:before]))
          items = items.where("(items.published_at, items.id) < (?, ?)", cursor.published_at, cursor.id)
        end
        page = items.limit(PAGE_SIZE).to_a
        attempted = Learning::Attempt.where(user: current_user, item: page).distinct.pluck(:item_id).to_set
        render json: {
          items: page.map { |item| ItemPayload.new(item, revealed: attempted.include?(item.id), user: current_user).as_json },
          next: page.size == PAGE_SIZE ? page.last.public_id : nil
        }
      end

      # GET /api/v1/items/:id (public id). Hidden fields appear once the user has attempted it.
      def show
        render json: ItemPayload.for(find_item, user: current_user).as_json
      end

      private

      def find_item
        Item.accessible_by(current_user).includes(:current_version, :source).find_by!(public_id: params[:id])
      end
    end
  end
end
