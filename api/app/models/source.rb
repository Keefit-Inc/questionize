class Source < ApplicationRecord
  has_many :items, dependent: :nullify
  validates :canonical_url, presence: true, uniqueness: true
end
