namespace :questionize do
  desc "Queue practice questions from the seed designs (db/seeds/designs.json). LEVELS=a,b limits levels; COUNT per design and level (default 2)."
  task seed_designs: :environment do
    data = JSON.parse(Rails.root.join("db/seeds/designs.json").read)
    only = ENV["LEVELS"].to_s.split(",").map(&:strip).presence
    count = ENV.fetch("COUNT", "2").to_i.clamp(1, 3)
    queued = 0
    data.fetch("designs").each do |design|
      levels = design.fetch("levels")
      levels &= only if only
      levels.each do |level|
        LevelPracticeJob.perform_later(design: design, level: level, practice_trap: design["practice_trap"], count: count, origin: "seed")
        queued += 1
      end
    end
    puts "Queued #{queued} jobs (#{count} question(s) each). Watch them with: bin/kamal logs"
  end
end
