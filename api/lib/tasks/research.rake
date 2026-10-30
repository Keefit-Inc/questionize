namespace :questionize do
  desc "Import a frozen, abstract replay benchmark from JSON on stdin. No question text is accepted."
  task research_import: :environment do
    data = JSON.parse($stdin.read)
    Research::Release.bootstrap!
    benchmark = Research::Benchmark.find_by(content_hash: data.fetch("hash"))
    unless benchmark
      benchmark = Research::Benchmark.create!(public_id: data.fetch("id"), name: "GMAT CR recorded decision replay v1",
        content_hash: data.fetch("hash"), cases: data.fetch("cases"),
        provenance: data.slice("parent_dataset_hash", "source_run", "builder_version", "excluded", "source_dataset_hash"))
    end
    Research::Benchmark.transaction do
      Research::Benchmark.where(subject: "CR", level: "gmat").update_all(enabled: false)
      benchmark.update!(enabled: true)
    end
    puts({ benchmark: benchmark.public_data, baseline: Research::Release.first.public_data }.to_json)
  end

  desc "Queue one bounded GMAT CR policy cycle (no Snap or Bank creation)."
  task research_cycle: :environment do
    cycle = Research::StartCycle.call
    puts({ id: cycle.public_id, status: cycle.status }.to_json)
  end

  desc "Print aggregate policy-cycle and active-service evidence."
  task research_status: :environment do
    puts Research::Feed.public_data.to_json
  end
end
