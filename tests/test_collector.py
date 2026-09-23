import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect_opportunities as c
class CollectorTests(unittest.TestCase):
 def item(self,url='https://example.org/job/1',source='a',checked='2026-09-21',deadline='2026-09-30'):
  return {'url':url,'source_id':source,'checked_at':checked+'T12:00:00+00:00','deadline':deadline,'title':'Education officer'}
 def test_dedup(self):
  j=self.item();self.assertEqual(len(c.merge([], [j,j], [{'id':'a','ok':True}], '2026-09-22')),1)
 def test_success_removes_withdrawn_offers(self):
  self.assertEqual(c.merge([self.item()],[],[{'id':'a','ok':True}],'2026-09-22'),[])
 def test_failure_keeps_recent_but_drops_stale_and_expired(self):
  rows=[self.item(),self.item('https://example.org/job/2',checked='2026-09-01'),self.item('https://example.org/job/3',deadline='2026-09-20')]
  self.assertEqual(len(c.merge(rows,[],[{'id':'a','ok':False}],'2026-09-22')),1)
 def test_format_change_is_not_a_success(self):
  with self.assertRaises(ValueError):c.parse_sap('<html>Service unavailable</html>',{},'2026-09-22')
 def test_deadline_is_calendar_valid(self):
  self.assertEqual(c.date_value('30/9/2026'),'2026-09-30')
  with self.assertRaises(ValueError):c.date_value('31/2/2026')
 def test_metadata_parser(self):
  s='<table id="searchresults"><tr class="data-row"><td><a href="/job/education/123/">Education &amp; training</a></td><td class="colLocation">Dakar, Senegal</td><td class="colFacility">Consultant</td><td class="colShifttype">30/9/2099</td></tr></table>'
  r=c.parse_sap(s,{'id':'a','name':'Source','organization':'Org','url':'https://example.org/'},'2026-09-22')[0]
  self.assertEqual(r['category'],'consultance');self.assertEqual(r['country'],'Senegal');self.assertEqual(r['title'],'Education & training')

class RelevanceTests(unittest.TestCase):
 def test_information_is_not_formation(self):
  import re
  self.assertIsNone(re.search(c.KEYWORDS,c.norm('Communication and Information Sector')))
 def test_international_consultant_is_not_intern(self):
  s='<table id="searchresults"><tr class="data-row"><td><a href="/job/ict/123/">International Consultant for Teacher Trainer on ICT Pedagogy</a></td><td class="colFacility">Consultant</td><td class="colShifttype">30/9/2099</td></tr></table>'
  j=c.parse_sap(s,{'id':'a','name':'Source','organization':'Org','url':'https://example.org/'},'2026-09-22')[0]
  self.assertEqual(j['category'],'consultance')

if __name__=='__main__':unittest.main()

class FeedTests(unittest.TestCase):
 def source(self):return dict(id='test',name='Test',organization='Test',url='https://example.org/rss')
 def test_rss_deadline_and_no_description_copy(self):
  s='<rss><channel><item><title>Education Research Fellow</title><link>https://example.org/offer</link><description>Closing Date: 30 Sep 2099</description></item></channel></rss>'
  j=c.parse_rss(s,self.source(),'2026-09-23')[0]
  self.assertEqual(j['deadline'],'2099-09-30');self.assertNotIn('description',j)
 def test_no_publication_date_as_deadline(self):
  s='<rss><channel><item><title>Education Fellow</title><link>https://example.org/offer</link><pubDate>30 Sep 2099</pubDate></item></channel></rss>'
  self.assertEqual(c.parse_rss(s,self.source(),'2026-09-23'),[])
 def test_french_ilo_deadline(self):
  s="<rss><channel><item><title>Expert compétences</title><link>https://example.org/offer</link><description>Date de clôture (minuit): 04 Octobre 2099.</description></item></channel></rss>"
  self.assertEqual(c.parse_rss(s,self.source(),'2026-09-23')[0]['deadline'],'2099-10-04')
 def test_cross_domain_listing_rejected(self):
  self.assertIsNone(c.metadata(self.source(),'Research Fellow','https://unrelated.org/offer','2099-10-04','2026-09-23'))
 def test_error_page_rejected(self):
  with self.assertRaises(ValueError):c.parse_rss('<html/>',self.source(),'2026-09-23')

 def test_unicef_listing(self):
  s='<div class="list-view--item"><a class="job-link" href="/en-us/job/123/test">Education Officer</a><span class="location">Dakar</span><span class="close-date"><time datetime="2099-10-03T00:00:00Z"></time></span></div>'
  j=c.parse_unicef(s,self.source(),'2026-09-23')[0]
  self.assertEqual(j['deadline'],'2099-10-03');self.assertEqual(j['location'],'Dakar')
 def test_euraxess_listing(self):
  s='<div id="job-teaser-content"><h3 class="ecl-content-block__title"><a href="/jobs/123"><span>Research Fellow</span></a></h3><div id="id-Application-Deadline"><time datetime="2099-10-03T00:00:00Z"></time></div></div>'
  self.assertEqual(c.parse_euraxess(s,self.source(),'2026-09-23')[0]['deadline'],'2099-10-03')
