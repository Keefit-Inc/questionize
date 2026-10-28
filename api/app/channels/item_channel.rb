# Live answer tallies for one item. Only users who have already answered it may subscribe,
# so the distribution never leaks before an attempt.
class ItemChannel < ApplicationCable::Channel
  def subscribed
    item = Item.accessible_by(current_user).find_by(public_id: params[:item_id])
    item && Learning::Attempt.exists?(user: current_user, item: item) ? stream_for(item) : reject
  end

  def self.broadcast_tally(item)
    version = item.current_version
    broadcast_to(item, { item_id: item.public_id, tally: version.tally, attempts_count: item.attempts_count })
  end
end
