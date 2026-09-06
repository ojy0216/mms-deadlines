require 'json'
require 'date'
require 'time'

module Jekyll
  class ScheduleGenerator < Generator
    safe true

    def escape_ics(value)
      value.to_s.gsub('\\', '\\\\').gsub("\n", '\\n').gsub(',', '\\,').gsub(';', '\\;')
    end

    def fold_line(line)
      chunks = ['']
      line.each_char do |char|
        chunks << ' ' if chunks.last.bytesize + char.bytesize > 75
        chunks[-1] += char
      end
      chunks.join("\r\n")
    end

    def calendar(records, site)
      lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//MMS//Conference Schedules//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH']
      records.each do |record|
        record['events'].each do |event|
          next if event['precision'] == 'tba'
          lines += ['BEGIN:VEVENT', "UID:#{record['id']}-#{event['kind']}@mms-deadlines", "DTSTAMP:#{Time.parse(event['checked_at']).utc.strftime('%Y%m%dT%H%M%SZ')}"]
          if event['precision'] == 'date'
            start = Date.parse(event['date'])
            finish = Date.parse(event['end'] || event['date']) + 1
            lines += ["DTSTART;VALUE=DATE:#{start.strftime('%Y%m%d')}", "DTEND;VALUE=DATE:#{finish.strftime('%Y%m%d')}"]
          else
            start = Time.parse(event['utc']).utc
            lines += ["DTSTART:#{start.strftime('%Y%m%dT%H%M%SZ')}", "DTEND:#{(start + 60).strftime('%Y%m%dT%H%M%SZ')}"]
          end
          lines << "SUMMARY:#{escape_ics("#{record['title']} #{record['year']} — #{event['kind']}")}"
          lines << "LOCATION:#{escape_ics(event['place'] || record['place'])}"
          lines << "DESCRIPTION:#{escape_ics("Official: #{event['date']} #{event['timezone']}\n#{event['sources'].join("\n")}")}"
          lines << "URL:#{site.config['url']}#{site.baseurl}/conference/?id=#{record['id']}"
          lines << 'END:VEVENT'
        end
      end
      (lines + ['END:VCALENDAR']).map { |line| fold_line(line) }.join("\r\n") + "\r\n"
    end

    def add(site, path, content)
      page = PageWithoutAFile.new(site, site.source, File.dirname(path), File.basename(path))
      page.content = content
      page.data['layout'] = nil
      site.pages << page
    end

    def generate(site)
      records = site.data['conferences'] || []
      return unless records.all? { |r| r['events'] }
      add(site, 'schedule.json', JSON.generate({conferences: records, status: site.data['sync_status']}))
      add(site, 'ai-deadlines.ics', calendar(records, site))
      records.each { |record| add(site, "calendar/#{record['id']}.ics", calendar([record], site)) }
    end
  end
end
