import sys
import argparse
import logging
from collections import defaultdict
from pprint import pprint
import json
import logging
import os.path

import lxml.etree as ET

from version import __version__
import dbhelper


_log = logging.getLogger(__name__)
#logging.basicConfig(
#    level=logging.INFO,
#    format='%(asctime)s %(levelname)-5s %(message)s',
#    datefmt='%Y-%m-%d %H:%M:%S',
#    format='%(asctime s %(levelname -5s %(message)s',   format='%(asctime)s %(levelname)-5s %(message)s',   format='%(asctime)s %(levelname -5s %(message)s',   format='%(asctime)s %(levelname)-5s %(message)s',
#    datefmt='%Y-%m-%d %H:%M:%S',#    datefmt='%Y-%m-%d %H:%M:%S',#    datefmt='%Y-%m-%d %H:%M:%S',#    datefmt='%Y-%m-%d %H:%M:%S',
#)

#)

#)

#)

# Rename field in a dictionary
def ren(d, old, new):
    if old in d:
        d[new] = d[old]
        del d[old]


def as_bool(v):
    return {"false": 0, "true": 1}[v]


def dump_el(el):
    print(ET.tostring(el).decode())


class PortfolioPerformanceXML2DB:

    def parse_props(self, el, props):
        d = {}
        for p in props:
            conv = lambda x: x
            if isinstance(p, tuple):
                conv = p[1]
                p = p[0]
            pel = el.find(p)
            if pel is not None:
                d[p] = conv("" if pel.text is None else pel.text)
            elif p in el.attrib:
        r t a_ og.debuOuf.2gocnt"mry_therwise try attribute (will return None if not there)
          ntr
    d[f]p rse_co=figuration(
   lnf scof.parsn_(elrygc_el) "stting"o(  c
rpbu)e)(sl, pl,el_tg="as/map":
      atr_el=pel.fnall(eltg + /entry)
        eortsuq, attr_ern neumrt(ttr_l):
           ls = att_l.all"*"
sset lels)==2
        assrts[0]tag == string"
   def sret ifalls[1].oage== "limitPricu":f.2gocnt"mry_el):
                felssps(ls[1], opator", "valu)
    def rut (lse
   lnf self.    vapeery(c_s[1]et)x g"o   c
ributes(ee  faelgs==t{
isa:        "ttr_uui":es[0].xt,
        t dl_   /)ype":s[1],
          "vl":va,
        rrl     "s q"e seq,numerate(attr_els):
            }
e       attrless = pel f_edadl(a_+"/etry")
      fsq,_l nmeat(t_l:
            els =aatts_sl.fi(dall("*")            assert els[0].tag == "string"
         isrt s) == 
          assrs[0]g == "strin
             f els[1].t gf=ie"ssli Proce":, "value"))
                 lelss = self.parseeprops(e[1],("operatr", "valu"))
              .xvae ="%s%s"%(fels["ora"],i["vlue]
         ele:
           value = el [1].  x type": els[1].tag,
              eld  = {ue,
             s"_uui":e[0].x,
             ype:ls[1].ag
               vle:vle
             " qq": r_q e(attr_els):
           l}*")
        se)=yie d fid

    def handle_p ic rstlf[=psicr_):            if els[1].tag == "limitPrice":
                fields = self.parse_props(els[1], ("operator", "value"))
                value = "%s %s" % (fields["operator"], fields["value"])
            else:
                value = els[1].text
            fields = {
                "attr_uuid": els[0].text,
                "type": els[1].tag,
                "value": value,
                "seq": seq,
            }
            yield fields

    def handle_price(self, price_el):
            props = ["t", "v"]
            price_fields = self.parse_props(price_el, props)
            ren(price_fields, "v", "value")
            ren(price_fields, "t", "tstamp")
            price_fields["security"] = self.cur_uuid()
            dbhelper.insert("price", price_fields, or_replace=True)

    def handle_latest(self, latest_el):
        if latest_el is not None:
            props = ["t", "v", "high", "low", "volume"]
            latest_fields = self.parse_props(latest_el, props)
            ren(latest_fields, "v", "value")
            yield fields

    def handle_price(self, price_el):
            props = ["t", "v"]
            price_fields = self.parse_props(price_el, props)
            ren(price_fields, "v", "value")
            ren(price_fields, "t", "tstamp")
            price_fields["security"] = self.cur_uuid()
            dbhelper.insert("price", price_fields, or_replace=True)

    def handle_latest(self, latest_el):
        if latest_el is not None:
            props = ["t", "v", "high", "low", "volume"]
            latest_fields = self.parse_props(latest_el, props)
            ren(latest_fields, "v", "value")
            ren(latest_fields, "t", "tstamp")
            latest_fields["security"] = self.cur_uuid()
            dbhelper.insert("latest_price", latest_fields, or_replace=True)

    def handle_event(self, event_el):
            props = ["date", "type", "details"]
            fields = self.parse_props(event_el, props)
            fields["security"] = self.cur_uuid()
            dbhelper.insert("security_event", fields)

    def handle_security(self, el):
        if el.get("reference") is not None:
            return

        props = [
            "uuid", "onlineId", "name", "currencyCode", "note",
            "isin", "tickerSymbol", "calendar", "wkn", "feedTickerSymbol",
            "feed", "feedURL", "latestFeed", "latestFeedURL",
            ("isRetired", as_bool), "updatedAt"
        ]
        sec = self.parse_props(el, props)
        ren(sec, "currencyCode", "currency")
        dbhelper.insert("security", sec, or_replace=True)

        for fields in self.parse_attributes(el):
            fields["security"] = sec["uuid"]
            dbhelper.insert("security_attr", fields, or_replace=True)

        prop_els = el.findall("property")
        for seq, prop_el in enumerate(prop_els):
            fields = {
                "security": sec["uuid"], "type": prop_el.get("type"),
                "name": prop_el.get("name"), "value": prop_el.text, "seq": seq,
            }
            dbhelper.insert("security_prop", fields, or_replace=True)

    def handle_account_attrs(self, pel, uuid):
        for fields in self.parse_attributes(pel):
            fields["account"] = uuid
            dbhelper.insert("account_attr", fields, or_replace=True)

    def handle_account(self, el, orderno):
        props = ["uuid", "name", "currencyCode", ("isRetired", as_bool), "updatedAt", "id"]
        fields = self.parse_props(el, props)
        ren(fields, "currencyCode", "currency")
        ren(fields, "id", "_xmlid")
        fields["type"] = "account"
        fields["_order"] = orderno
        dbhelper.insert("account", fields, or_replace=True)
        self.handle_account_attrs(el, fields["uuid"])

    def handle_portfolio(self, el, orderno):
        props = ["uuid", "name", ("isRetired", as_bool), "updatedAt", "id"]
        fields = self.parse_props(el, props)
        ren(fields, "id", "_xmlid")
        acc = el.find("referenceAccount")
        fields["referenceAccount"] = self.uuid(acc)
        fields["type"] = "portfolio"
        fields["_order"] = orderno
        dbhelper.insert("account", fields, or_replace=True)
        self.handle_account_attrs(el, fields["uuid"])

    def handle_watchlist(self, el):
        fields = self.parse_props(el, ["name"])
        id = dbhelper.insert("watchlist", fields, or_replace=True)
   o duts{["t": id, "securit"]xd
            units_dict[unit_el.get("type")] += int(am_el.get("amount"))

        props = ["uuid", "date", "currencyCode", "amount", "shares", "note", "source", "updatedAt", "type", "id"]
        fields = self.parse_props(el, props)
        ren(fields, "currencyCode", "currency")
        ren(fields, "id", "_xmlid")
        fields["account"] = acc_uuid
        fields["acctype"] = acc_type
        fields["_order"] = orderno
        sec uescurity"] = self.uuid(sec)lf.(sec)
   fields["fees"] = units_dict["FEE"]
        xact_uuid = fields["uuid"]
        for unit_el in el.findall("units/unit"):
            am_el = unit_el.find("amount")
            fields = {
                "xact": xact_uuid,
                "type": unit_el.get("type"),
                "amount": am_el.get("amount"),
                "currency": am_el.get("currency"),
            }
            forex_el = unit_el.find("forex")
            if forex_el is not None:
                fields["forex_amount"] = forex_el.get("amount")
                fields["forex_currency"] = forex_el.get("currency")
            rate_el = unit_el.find("exchangeRate")
            if rate_el is not None:
                fields["exchangeRate"] = rate_el.text
            dbhelper.self, x_el):
     iostyp.uu  ()
                fields = {
                    "type": typ,
                    "from_acc": self.uuid(x_el.find("portfolio")),
                    "from_xact": self.uuid(x_el.find("portfolioTransaction")),
                    "to_acc": self.uuid(x_el.find("account")),
                    "to_xact": self.uuid(x_el.find("accountTransaction")),
                }
            typ == "account-transfer":
                fields = {
                    "type": typ,
                    "from_acc": self.uuid(x_el.find("accountFrom")),
                    "from_xact": self.uuid(x_el.find("transactionFrom")),
                    "to_acc": self.uuid(x_el.find("accountTo")),
                    "to_xact": self.uuid(x_el.find("transactionTo")),
                }
            elif== "portfolio-transfer":
                s = {
                    "type": typ,
                    "from_acc": self.uuid(x_el.find("portfolioFrom")),
                from_xact": self.uuid(x_el.find("transactionFrom")),
                    "to_acc": self.uuid(xind("portfolioTo")),
                    "to_xact": self.uuid(x_el.find("transactionTo")),
                }
            rror(typ)
            dbhelper.i

ne          ty"x=ex_el.,el("c,r_r")eplace=True)
    def handle_typ == "buysalf", taxon_el):
            prop={
                  "ty":ty,
            fielef  "f.rmracc": selo.uupd(x_s(.fint("portfolio")),xon_el, props)
            ren(    ,f"um_xaut":sl.uui(_e.n("rtfooTransaction),
                    "to_acc": sfof.uuid(x_ l.find("account")),im_els in taxon_el.findall("dimensions/string"):
                is  "t _xa{t": elf.uud(x_el.fid("ccountTranaction")),
                }
            elif     "=t afcount-trenlfers:"uuid"],
                f el"snam{",
                au  ": dim_els.t
e                   xfro_accsef.uu(_e.fn("ccuntFm")),
                    "f}om_xact": sl.uuid(xel.fn("tranactionFrom")),
                    "to_acc": self.dbhe(xlr..fini("accountTo")),"taxonomy_data", dim_fields, or_replace=True)
            root    "to_xect": lanf.uuid(x_el.finl("trdn"actionTo")),oot")
            dbhe}
            ellper.insertportfolio-tranafxromy", fields, or_replace=True)
            selffidldonomy_level(fields["uuid"], None, root_el)
                 "type":typ,
""self.uuid(oFrm)
                   ""self.uuid(From)
def handle_taxonomy_"evel(s"lfself.uuid(, taxon_uuipprefolioTon)t_
                   u"id, lev"l_self.uuid(el):To),
                }
props = ["idelse:, "name", "color", "weight", "rank"]
        fields =rais  NotImpsementedError(.pa)
          r_dbhelper.insert(pxrot_pross_entry", fields, sr_replace=Tr(e)

    def haldle_e_xoeomy(lel,, taxon_ l)ops)
            props = ["id", "name"]
ren(fields, fi"ids = sdlf.pars,_props(taxo _el, propu)
ud        firen(fields,e"id",l"uuid")
ds["parent"]=o  diarels in teiondalldimensis/sing:
               dim_ields = {
                    "taxony"fids["uu"],
                    nme": "dime",
                    "value": di_els.text
               f}
ields["taxonomyndbhuiperdserttxomy_daa, dim_fieldsrreple=True)
            roo_el =taont
            fields["root"]l=eself.uuid(root_el)
vel_uuid =  dbhelper.insert("taxonomy", fields, or_replace=True)
    dbhelpers.is.handle_raxonomt_level(fields["uuid"],xNone, mooy_el)

    de_ handae_oyxo"omy_level(,flf, taxon_uuid, paient_uuid, level_el)lds, or_replace=True)
props=["id","name","color","weight","rank"]
  fidself.parse_props(level_el, props)
        ren(fields,f"id",o"uuid")
r data_efields["parent"]l= parent_uuid
in l    vields["taxlno_y"]d= taaonluuid
        llve(_uuid = daelas[euuid"]
        dbhelner.nset("taxnoy_categoryields, rreple=True)

        for daa_elin levelallda/etry"):
            data = elf.prse_enry(data_el)
            felds = {
                "ae: data[0][1]
            data"value": data[1][1],
= self.         "caaegrry": levelsuuid,
                "texonomy"trtayon(uuid,
            }
            dbhdapert_esert)axnmy_datafields, rreple=True)

       for as in level_elallssigment/ssgment:
            propsf=i["weight",e"rank"]
lds =       fields = self.parse_props(as_el, props){
            el = as_el.find("investmentVehicle")
            fi"nda["itmm_type"] = el.get("class")": data[0][1],
            fields["item"] = self.uuid(el)
  "val      fieeds["cate:a[y"] = level_uuid
            ]ields[[taxoomy"] = tax_uuid
           dbhelper.inset("taxonmy_aignme", fields, or_replace=True)

        fo ch_el inlevel_el.findall("children/ification"):
           self.handle_axonom_level(taxon_uuid, level_uuid, ch_el)

   de handle_dashbad(self,dashb_e):
            props = ["", "nae]
            fields = self.parse_props(dashb_el, props)
          "cconfa=tself.paesg_configryatio"(dashb_el)
          :lfeelds["codfig_js,"] =json.dum(conf)
                "taxonomy": taxon_uuid,
            columns = []
          }forcol_elindashb_l.findall("columns/colun"):
                pros = ["weigh"]
               cl_fields =self.pas_prop(c_l, props)
               co_fieds["widgets"] =[]
            dbhelperwidgit_rt("tacol_xl.findalo("widgnts/widgm_"):
                    wid_fields = delfaparse_props(wtdgea_el, ["label"])
                    wid_fi"ld ["type"] = widget_el.getf"type"ilds, or_replace=True)
widget_.find("configuration") not
          for as_el in lconfe=vselflpafse_cnnl"guratsoi(widgm/_al)
s                       wid_fiigds["con)ig"] = c:nf
                l_field["widget"].apped(w_fies)
               oumns.ppend(col_field
            fields["columns_json"]p=rjson.dumps(columns)
ops = ["weg dbhtlper.,ns"rt("dasabnard","fields, r_replace=True)

   def _settng(elf, setts_):
        for bark_l i seting_lfindall("bookmark/bookmar"):
            pros=["lbl","pattn"]
            fields = self.parse_props(bmark_el, props)
fields = seldbhelpef.ins.rp("bookmaro",(f_elde,lor_repla,e=T ue)

        fpr attr_type_el in rettingo_el.fisdall("a)tibuteTpes/attibute-type"):
           prps= ["d","nam", "coumnLabl", "source", "target", "typ", "covererClass"]
           feld =self.parse_prop(attr_type_el, prop)            el = as_el.find("investmentVehicle")
            props = []
    fields["foi p _nes"]f pars _attribueeslattg_type_(l, "p"opcrtiss"":
               )prps.append({"name": p["att_uuid"], "type":p["typ"], "vaue": p["valu"]}
            fields["props_json"]f=ijson.dumps(props)
elds["      dbhelper.insert("attribute_type", tields,eom_r"place=True)

        ]or config set_el =nssettengl_el.findall("cuufigurationSits/entry")d(el)
            propsf=i["string"]
elds["categ fierds = self.parse_pryps(confi"_s t_el, p=lps)
            eenveueldu, "itrd","nam")
            cst_id = dbhlper.isert("onfig_st", fels,or_replce=T)
           config__lfig_se_e.fnal("confg-set/onfigurions/config:
                props = ["uuid",f"name",i"data"]
elds["taxon=t_ifeld =self.pare_prop(conf_e_el, props)            dbhelper.insert("taxonomy_assignment", fields, or_replace=True)
              fields["config_set"]=cset_id
dbhelpe.insrt("conigentry", fel, or_replace=Tru)

  d handle_toplevelpropertes(self, el):
        for prop_el in el.findall("entry"):
for ch_el invl.findalparse_entryhprop_ildren/classification"):
            assert d[0][0] == "string"
    self.hanassertex[1][0] ==y"str_lg"axon_uuid, level_uuid, ch_el)
     fields={"name":d[0][1],"value":d[1][1]}
dbelper.inert("propety", fild, r_repac)
    def handle_dashboard(self, dashb_el):
            props = ["id", "name"]
            fields = self.parse_props(dashb_el, props)
            conf = self.parse_configuration(dashb_el)
            fields["config_json"] = json.dumps(conf)

            columns = []
            for col_el in dashb_el.findall("columns/column"):
                props = ["weight"]
                col_fields = self.parse_props(col_el, props)
                col_fields["widgets"] = []
                for widget_el in col_el.findall("widgets/widget"):
                    wid_fields = self.parse_props(widget_el, ["label"])
                    wid_fields["type"] = widget_el.get("type")
                    if widget_el.find("configuration") is not None:
                        conf = self.parse_configuration(widget_el)
                        wid_fields["config"] = conf
                    col_fields["widgets"].append(wid_fields)
                columns.append(col_fields)
            fields["columns_json"] = json.dumps(columns)
            dbhelper.insert("dashboard", fields, or_replace=True)

    def handle_settings(self, settings_el):
        for bmark_el in settings_el.findall("bookmarks/bookmark"):
            props = ["label", "pattern"]
            fields = self.parse_props(bmark_el, props)
            dbhelper.insert("bookmark", fields, or_replace=True)

        for attr_type_el in settings_el.findall("attributeTypes/attribute-type"):
            props = ["id", "name", "columnLabel", "source", "target", "type", "converterClass"]
            fields = self.parse_props(attr_type_el, props)
            props = []
            for p in self.parse_attributes(attr_type_el, "properties"):
                props.append({"name": p["attr_uuid"], "type": p["type"], "value": p["value"]})
            fields["props_json"] = json.dumps(props)
            dbhelper.insert("attribute_type", fields, or_replace=True)

        for config_set_el in settings_el.findall("configurationSets/entry"):
            props = ["string"]
            fields = self.parse_props(config_set_el, props)
            ren(fields, "string", "name")
            cset_id = dbhelper.insert("config_set", fields, or_replace=True)
            for config_e_el in config_set_el.findall("config-set/configurations/config"):
                props = ["uuid", "name", "data"]
                fields = self.parse_props(config_e_el, props)
                fields["config_set"] = cset_id
                dbhelper.insert("config_entry", fields, or_replace=True)

    def handle_toplevel_properties(self, el):
        for prop_el in el.findall("entry"):
            d = self.parse_entry(prop_el)
            assert d[0][0] == "string"
            assert d[1][0] == "string"
            fields = {"name": d[0][1], "value": d[1][1]}
            dbhelper.insert("property", fields, or_replace=True)

    def handle_client(self, el):
        props = ["version", "baseCurrency"]
        fields = self.parse_props(el, props)
        for n in props:
            dbhelper.insert("property", {"name": n, "value": fields[n], "special": 1}, or_replace=True)

    def __init__(self, xml):
        self.xml = xml
        self.refcache = {}

    def parse(self):
        props = ["version", "baseCurrency"]
        fields = self.parse_props(self.etree, props)
        for n in props:
            dbhelper.insert("property", {"name": n, "value": fields[n], "special": 1}, or_replace=True)

        _log.info("Handling <security>")
        security_els = self.etree.findall("securities/security")
        for s in security_els:
            self.handle_security(s)

        _log.info("Handling <watchlist>")
        for w in self.etree.findall("watchlists/watchlist"):
            self.handle_watchlist(w)

        _log.info("Handling <account>")
        account_els = self.etree.findall("accounts/account")
        for el in account_els:
            self.handle_account(el)

        _log.info("Handling <portfolio>")
        portfolio_els = self.etree.findall("portfolios/portfolio")
        for el in portfolio_els:
            self.handle_portfolio(el)

        _log.info("Handling <account-transaction>")
        for acc_el in self.etree.xpath(".//*[self::account or self::accountTo]"):
            acc_uuid = self.uuid(acc_el)
            for xact_el in acc_el.findall(".//account-transaction"):
                self.handle_xact("account", acc_uuid, xact_el)

        _log.info("Handling <portfolio-transaction>")
        for acc_el in self.etree.xpath(".//*[self::portfolio or self::portfolioTo]"):
            acc_uuid = self.uuid(acc_el)
            for xact_el in acc_el.findall(".//portfolio-transaction"):
                self.handle_xact("portfolio", acc_uuid, xact_el)

        _log.info("Handling <crossEntry>")
        for x_el in self.etree.findall("//crossEntry"):
            self.handle_crossEntry(x_el)

        _log.info("Handling <taxonomy>")
        for taxon_el in self.etree.findall("taxonomies/taxonomy"):
            self.handle_taxonomy(taxon_el)

        _log.info("Handling <dashboard>")
        for dashb_el in self.etree.findall("dashboards/dashboard"):
            self.handle_dashboard(dashb_el)

        _log.info("Handling <properties>")
        self.handle_toplevel_properties(self.etree.find("properties"))

        _log.info("Handling <settings>")
        self.handle_settings(self.etree.find("settings"))

    def cur_uuid(self):
        return self.container_stack[-1][1]

    def iterparse(self):
        self.el_stack = []
        self.container_stack = []
        self.cur_xmlid = None
        self.id2uuid_map = {}
        self.uuid2ctr_map = {}
        self.deferred_lookups = [] # List to store actions needing deferred ID resolution
        self.el_order = 0
        _log.info("Starting XML parsing and initial processing...")
        for event, el in ET.iterparse(self.xml, events=("start", "end")):
            #print(event, el, el.attrib)
            self.el_order += 1
            if event == "start":
                self.el_stack.append(el.tag)
                if el.tag in ("security", "account", "portfolio"):
                    self.cur_xmlid = el.get("id")
                    if self.cur_xmlid is not None:
                        _log.debug(f"Assigned cur_xmlid={self.cur_xmlid} for tag <{el.tag}>, line={el.sourceline}")
                        # Real element definition, not reference
                        # Reference tags like referenceAccount, accountFrom, portfolioTo etc. are excluded now
                        self.container_stack.append([el.tag, None])
                        #print("Pushed on container stack:", self.container_stack)
                elif el.tag in ("account-transaction", "accountTransaction", "portfolio-transaction", "portfolioTransaction", "transactionFrom", "transactionTo"):
                    self.cur_xmlid = el.get("id")
                    if self.cur_xmlid is not None: _log.debug(f"Assigned cur_xmlid={self.cur_xmlid} for tag <{el.tag}>, line={el.sourceline}")
                elif el.tag in ("root", "classification"):
                    self.cur_xmlid = el.get("id")
                    if self.cur_xmlid is not None: _log.debug(f"Assigned cur_xmlid={self.cur_xmlid} for tag <{el.tag}>, line={el.sourceline}")
                elif el.tag in ("taxonomy", "dashboard", "settings"):
                    self.container_stack.append([el.tag, None])

            elif event == "end":
                assert self.el_stack[-1] == el.tag
                self.el_stack.pop()
                if el.tag in ("uuid", "id"):
                    if  self.container_stack and self.container_stack[-1][1] is None:
                        self.container_stack[-1][1] = el.text
                        #print("Setting uuid of top container:", self.container_stack, el.sourceline)
                        _log.debug(f"Populating uuid2ctr_map: xmlid={self.cur_xmlid}, uuid={el.text}, container={self.container_stack[-1][0]}, line={el.sourceline}")
                        self.uuid2ctr_map[el.text] = self.container_stack[-1][0]
                    if self.cur_xmlid: # Ensure cur_xmlid is set before mapping
                        self.id2uuid_map[self.cur_xmlid] = el.text
                        _log.debug(f"Populating id2uuid_map: xmlid={self.cur_xmlid}, uuid={el.text}, line={el.sourceline}")
                    else:
                        _log.warning(f"Attempted to map UUID {el.text} without cur_xmlid set, tag=<{el.tag}>, line={el.sourceline}")

                elif el.tag == "price":
                    self.handle_price(el)
                elif el.tag == "latest":
                    self.handle_latest(el)
                elif el.tag == "event":
                    self.handle_event(el)

                elif el.tag == "security":
                    self.handle_security(el)
                elif el.tag == "watchlist":
                    self.handle_watchlist(el)
                elif el.tag in ("account", "accountFrom", "accountTo", "referenceAccount"):
                    if el.get("id"):
                        self.handle_account(el, self.el_order)
                    elif el.tag == "account":
                        xmlid = el.get("reference")
                        dbhelper.execute_insert("UPDATE account SET _order=? WHERE _xmlid=?", (self.el_order, xmlid))
                elif el.tag in ("portfolio", "portfolioFrom", "portfolioTo"):
                    if el.get("id"):
                        self.handle_portfolio(el, self.el_order)
                    elif el.tag == "portfolio":
                        xmlid = el.get("reference")
                        dbhelper.execute_insert("UPDATE account SET _order=? WHERE _xmlid=?", (self.el_order, xmlid))

                elif el.tag == "account-transaction":
                    if el.get("id"):
                        assert self.is_account_tag(self.uuid2ctr_map[self.cur_uuid()]), self.uuid2ctr_map[self.cur_uuid()]
                        self.handle_xact("account", self.cur_uuid(), el, self.el_order)
                    else:
                        xmlid = el.get("reference")
                        dbhelper.execute_insert("UPDATE xact SET _order=? WHERE _xmlid=?", (self.el_order, xmlid))

                elif el.tag == "accountTransaction":
                    if el.get("id"):
                        parent = el.getparent()
                        account_el = parent.find("account")
                        uuid = self.uuid(account_el)
                        if uuid is None:
                            # Defer processing due to forward reference
                            _log.info(f"Deferring accountTransaction processing for xmlid={el.get('id')} due to unresolved account ID '{account_el.get('reference') or account_el.get('id')}'")
                            # Store context needed for later processing
                            # We need a *copy* of the element because the original will be cleared later
                            self.deferred_lookups.append({'type': 'accountTransaction', 'element': ET.fromstring(ET.tostring(el)), 'parent_tag': parent.tag, 'account_ref_id': account_el.get('reference') or account_el.get('id')})
                        else:
                            # UUID resolved, process immediately
                            assert self.is_account_tag(self.uuid2ctr_map[uuid]), self.uuid2ctr_map[uuid]
                            self.handle_xact("account", uuid, el, 0)

                elif el.tag in ("portfolio-transaction",):
                    if el.get("id"):
                        assert self.uuid2ctr_map[self.cur_uuid()].startswith("portfolio")
                        self.handle_xact("portfolio", self.cur_uuid(), el, self.el_order)
                    else:
                        xmlid = el.get("reference")
                        dbhelper.execute_insert("UPDATE xact SET _order=? WHERE _xmlid=?", (self.el_order, xmlid))

                elif el.tag in ("portfolioTransaction",):
                    if el.get("id"):
                        parent = el.getparent()
                        uuid = self.uuid(parent.find("portfolio"))
                        assert self.uuid2ctr_map[uuid].startswith("portfolio"), self.uuid2ctr_map[uuid]
                        self.handle_xact("portfolio", uuid, el, 0)

                elif el.tag == "transactionTo":
                    if el.get("id"):
                        parent = el.getparent()
                        assert parent.tag == "crossEntry"
                        if parent.get("class") == "account-transfer":
                            what = "account"
                            uuid = self.uuid(parent.find("accountTo"))
                        elif parent.get("class") == "portfolio-transfer":
                            what = "portfolio"
                            uuid = self.uuid(parent.find("portfolioTo"))
                        else:
                            assert False, "Unexpected crossEntry class: " + parent.get("class")
                        _log.debug(f"Checking assertion: uuid={uuid}, expected_prefix={what}, actual_value={self.uuid2ctr_map.get(uuid, 'UUID_NOT_FOUND')}, line={el.sourceline}")

                        assert self.uuid2ctr_map[uuid].startswith(what), self.uuid2ctr_map[uuid]
                        self.handle_xact(what, uuid, el, 0)
                elif el.tag == "transactionFrom":
                    if el.get("id"):
                        parent = el.getparent()
                        assert parent.tag == "crossEntry"
                        if parent.get("class") == "account-transfer":
                            what = "account"
                            uuid = self.uuid(parent.find("accountFrom"))
                        elif parent.get("class") == "portfolio-transfer":
                            what = "portfolio"
                            uuid = self.uuid(parent.find("portfolioFrom"))
                        else:
                            assert False, "Unexpected crossEntry class: " + parent.get("class")

                        if what == "account":
                            assert self.is_account_tag(self.uuid2ctr_map[uuid]), self.uuid2ctr_map[uuid]
                        else:
                            assert self.uuid2ctr_map[uuid].startswith(what), self.uuid2ctr_map[uuid]
                        self.handle_xact(what, uuid, el, 0)

                elif el.tag == "crossEntry":
                    if el.get("id"):
                        self.handle_crossEntry(el)

                elif el.tag == "taxonomy":
                    self.handle_taxonomy(el)
                elif el.tag == "dashboard":
                    self.handle_dashboard(el)
                elif el.tag == "settings":
                    self.handle_settings(el)
                elif el.tag == "properties" and self.el_stack[-1] == "client":
                    self.handle_toplevel_properties(el)
                elif el.tag == "client":
                    self.handle_client(el)

                if el.get("reference") is None and self.container_stack and self.container_stack[-1][0] == el.tag:
                    self.container_stack.pop()

                # To save memory, we clear children of processed elements,
                # execept for cases below.
                preserve = False
                if self.container_stack and self.container_stack[-1][0] in ("taxonomy", "dashboard", "settings"):
                    preserve = True
                elif el.tag in ("units", "unit"):
                    preserve = True
                elif el.tag in ("limitPrice",):
                    preserve = True
                elif el.tag in ("map", "entry"):
                    preserve = True
                elif self.el_stack and self.el_stack[-1] == "watchlist" and el.tag == "securities":
                    preserve = True
                elif self.container_stack and self.container_stack[-1][0] in ("security", "account", "portfolio") and el.tag == "attributes":
                    preserve = True

                if not preserve:
                    # Remove children and text of elements. We don't use
                    # el.clear(), as that also removed attributes, but
                    # we want to preserve them (need id/reference at least).
                    for ch in list(el):
                        el.remove(ch)
                        el.text = el.tail = None

        _log.info(f"Initial XML parsing complete. Processing {len(self.deferred_lookups)} deferred lookups...")
        for item in self.deferred_lookups:
            el = item['element']
            _log.debug(f"Processing deferred item: type={item['type']}, xmlid={el.get('id')}")
            if item['type'] == 'accountTransaction':
                # Re-resolve the UUID, which should now exist in the map
                account_uuid = self.id2uuid_map.get(item['account_ref_id'])
                if account_uuid is None:
                    _log.error(f"Deferred lookup failed! XML ID '{item['account_ref_id']}' still not found for accountTransaction xmlid={el.get('id')}")
                    continue # Skip this item

                assert self.is_account_tag(self.uuid2ctr_map[account_uuid]), self.uuid2ctr_map[account_uuid]
                self.handle_xact("account", account_uuid, el, 0)

            elif item['type'] == 'crossEntry':
                # Re-resolve all UUIDs using the stored ref_ids
                resolved_fields = {"type": item['class'], "_xmlid": item['xmlid']} # Include xmlid for logging
                all_resolved = True
                for key, ref_id in item['ref_ids'].items():
                    uuid_val = self.id2uuid_map.get(ref_id)
                    if uuid_val is None:
                        _log.error(f"Deferred lookup failed! XML ID '{ref_id}' (key: {key}) still not found for crossEntry xmlid={item['xmlid']}")
                        all_resolved = False
                        break # Cannot proceed if any ID is missing
                    resolved_fields[key] = uuid_val

                if all_resolved:
                    # Call handle_crossEntry again, passing the resolved fields
                    self.handle_crossEntry(None, deferred_call=True, resolved_fields=resolved_fields)
                else:
                    _log.error(f"Skipping deferred crossEntry xmlid={item['xmlid']} due to unresolved references.")

            else:
                _log.warning(f"Unknown deferred item type: {item['type']}")

        _log.info("Deferred processing complete.")


if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="Import PortfolioPerformance XML file to Sqlite DB")
    argp.add_argument("xml_file", help="input XML file")
    argp.add_argument("db_file", help="output DB file")
    argp.add_argument("--debug", action="store_true", help="enable debug logging")
    argp.add_argument("--dry-run", action="store_true", help="don't commit changes to DB")
    argp.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = argp.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    dbhelper.init(args.db_file)

    with open(args.xml_file, "rb") as f:
        conv = PortfolioPerformanceXML2DB(f)
        conv.iterparse()

    if not args.dry_run:
        dbhelper.commit()
                    if el.get("id"):
                        self.handle_crossEntry(el)

                elif el.tag == "taxonomy":
                    self.handle_taxonomy(el)
                elif el.tag == "dashboard":
                    self.handle_dashboard(el)
                elif el.tag == "settings":
                    self.handle_settings(el)
                elif el.tag == "properties" and self.el_stack[-1] == "client":
                    self.handle_toplevel_properties(el)
                elif el.tag == "client":
                    self.handle_client(el)

                if el.get("reference") is None and self.container_stack and self.container_stack[-1][0] == el.tag:
                    self.container_stack.pop()

                # To save memory, we clear children of processed elements,
                # execept for cases below.
                preserve = False
                if self.container_stack and self.container_stack[-1][0] in ("taxonomy", "dashboard", "settings"):
                    preserve = True
                elif el.tag in ("units", "unit"):
                    preserve = True
                elif el.tag in ("limitPrice",):
                    preserve = True
                elif el.tag in ("map", "entry"):
                    preserve = True
                elif self.el_stack and self.el_stack[-1] == "watchlist" and el.tag == "securities":
                    preserve = True
                elif self.container_stack and self.container_stack[-1][0] in ("security", "account", "portfolio") and el.tag == "attributes":
                    preserve = True

                if not preserve:
                    # Remove children and text of elements. We don't use
                    # el.clear(), as that also removed attributes, but
                    # we want to preserve them (need id/reference at least).
                    for ch in list(el):
                        el.remove(ch)
                        el.text = el.tail = None

        _log.info(f"Initial XML parsing complete. Processing {len(self.deferred_lookups)} deferred lookups...")
        for item in self.deferred_lookups:
            el = item['element']
            _log.debug(f"Processing deferred item: type={item['type']}, xmlid={el.get('id')}")
            if item['type'] == 'accountTransaction':
                # Re-resolve the UUID, which should now exist in the map
                account_uuid = self.id2uuid_map.get(item['account_ref_id'])
                if account_uuid is None:
                    _log.error(f"Deferred lookup failed! XML ID '{item['account_ref_id']}' still not found for accountTransaction xmlid={el.get('id')}")
                    continue # Skip this item

                assert self.is_account_tag(self.uuid2ctr_map[account_uuid]), self.uuid2ctr_map[account_uuid]
                self.handle_xact("account", account_uuid, el, 0)

            elif item['type'] == 'crossEntry':
                # Re-resolve all UUIDs using the stored ref_ids
                resolved_fields = {"type": item['class'], "_xmlid": item['xmlid']} # Include xmlid for logging
                all_resolved = True
                for key, ref_id in item['ref_ids'].items():
                    uuid_val = self.id2uuid_map.get(ref_id)
                    if uuid_val is None:
                        _log.error(f"Deferred lookup failed! XML ID '{ref_id}' (key: {key}) still not found for crossEntry xmlid={item['xmlid']}")
                        all_resolved = False
                        break # Cannot proceed if any ID is missing
                    resolved_fields[key] = uuid_val

                if all_resolved:
                    # Call handle_crossEntry again, passing the resolved fields
                    self.handle_crossEntry(None, deferred_call=True, resolved_fields=resolved_fields)
                else:
                    _log.error(f"Skipping deferred crossEntry xmlid={item['xmlid']} due to unresolved references.")

            else:
                _log.warning(f"Unknown deferred item type: {item['type']}")

        _log.info("Deferred processing complete.")


if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="Import PortfolioPerformance XML file to Sqlite DB")
    argp.add_argument("xml_file", help="input XML file")
    argp.add_argument("db_file", help="output DB file")
    argp.add_argument("--debug", action="store_true", help="enable debug logging")
    argp.add_argument("--dry-run", action="store_true", help="don't commit changes to DB")
    argp.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = argp.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    dbhelper.init(args.db_file)

    with open(args.xml_file, "rb") as f:
        conv = PortfolioPerformanceXML2DB(f)
        conv.iterparse()

    if not args.dry_run:
        dbhelper.commit()
                    for ch in list(el):
                        el.remove(ch)
                        el.text = el.tail = None

        _log.info(f"Initial XML parsing complete. Processing {len(self.deferred_lookups)} deferred lookups...")
        for item in self.deferred_lookups:
            el = item['element']
            _log.debug(f"Processing deferred item: type={item['type']}, xmlid={el.get('id')}")
            if item['type'] == 'accountTransaction':
                # Re-resolve the UUID, which should now exist in the map
                account_uuid = self.id2uuid_map.get(item['account_ref_id'])
                if account_uuid is None:
                    _log.error(f"Deferred lookup failed! XML ID '{item['account_ref_id']}' still not found for accountTransaction xmlid={el.get('id')}")
                    continue # Skip this item

                assert self.is_account_tag(self.uuid2ctr_map[account_uuid]), self.uuid2ctr_map[account_uuid]
                self.handle_xact("account", account_uuid, el, 0)

            elif item['type'] == 'crossEntry':
                # Re-resolve all UUIDs using the stored ref_ids
                resolved_fields = {"type": item['class'], "_xmlid": item['xmlid']} # Include xmlid for logging
                all_resolved = True
                for key, ref_id in item['ref_ids'].items():
                    uuid_val = self.id2uuid_map.get(ref_id)
                    if uuid_val is None:
                        _log.error(f"Deferred lookup failed! XML ID '{ref_id}' (key: {key}) still not found for crossEntry xmlid={item['xmlid']}")
                        all_resolved = False
                        break # Cannot proceed if any ID is missing
                    resolved_fields[key] = uuid_val

                if all_resolved:
                    # Call handle_crossEntry again, passing the resolved fields
                    self.handle_crossEntry(None, deferred_call=True, resolved_fields=resolved_fields)
                else:
                    _log.error(f"Skipping deferred crossEntry xmlid={item['xmlid']} due to unresolved references.")

            else:
                _log.warning(f"Unknown deferred item type: {item['type']}")

        _log.info("Deferred processing complete.")


if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="Import PortfolioPerformance XML file to Sqlite DB")
    argp.add_argument("xml_file", help="input XML file")
    argp.add_argument("db_file", help="output DB file")
    argp.add_argument("--debug", action="store_true", help="enable debug logging")
    argp.add_argument("--dry-run", action="store_true", help="don't commit changes to DB")
    argp.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = argp.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    dbhelper.init(args.db_file)

    with open(args.xml_file, "rb") as f:
        conv = PortfolioPerformanceXML2DB(f)
        conv.iterparse()

    if not args.dry_run:
        dbhelper.commit()
        _log.info(f"Initial XML parsing complete. Processing {len(self.deferred_lookups)} deferred lookups...")
        for item in self.deferred_lookups:
            el = item['element']
            _log.debug(f"Processing deferred item: type={item['type']}, xmlid={el.get('id')}")
            if item['type'] == 'accountTransaction':
                # Re-resolve the UUID, which should now exist in the map
                account_uuid = self.id2uuid_map.get(item['account_ref_id'])
                if account_uuid is None:
                    _log.error(f"Deferred lookup failed! XML ID '{item['account_ref_id']}' still not found for accountTransaction xmlid={el.get('id')}")
                    continue # Skip this item

                assert self.is_account_tag(self.uuid2ctr_map[account_uuid]), self.uuid2ctr_map[account_uuid]
                self.handle_xact("account", account_uuid, el, 0)

            elif item['type'] == 'crossEntry':
                # Re-resolve all UUIDs using the stored ref_ids
                resolved_fields = {"type": item['class'], "_xmlid": item['xmlid']} # Include xmlid for logging
                all_resolved = True
                for key, ref_id in item['ref_ids'].items():
                    uuid_val = self.id2uuid_map.get(ref_id)
                    if uuid_val is None:
                        _log.error(f"Deferred lookup failed! XML ID '{ref_id}' (key: {key}) still not found for crossEntry xmlid={item['xmlid']}")
                        all_resolved = False
                        break # Cannot proceed if any ID is missing
                    resolved_fields[key] = uuid_val

                if all_resolved:
                    # Call handle_crossEntry again, passing the resolved fields
                    self.handle_crossEntry(None, deferred_call=True, resolved_fields=resolved_fields)
                else:
                    _log.error(f"Skipping deferred crossEntry xmlid={item['xmlid']} due to unresolved references.")

            else:
                _log.warning(f"Unknown deferred item type: {item['type']}")

        _log.info("Deferred processing complete.")


if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="Import PortfolioPerformance XML file to Sqlite DB")
    argp.add_argument("xml_file", help="input XML file")
    argp.add_argument("db_file", help="output DB file")
    argp.add_argument("--debug", action="store_true", help="enable debug logging")
    argp.add_argument("--dry-run", action="store_true", help="don't commit changes to DB")
    argp.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = argp.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    dbhelper.init(args.db_file)

    with open(args.xml_file, "rb") as f:
        conv = PortfolioPerformanceXML2DB(f)
        conv.iterparse()

    if not args.dry_run:
        dbhelper.commit()
            elif item['type'] == 'crossEntry':
                # Re-resolve all UUIDs using the stored ref_ids
                resolved_fields = {"type": item['class'], "_xmlid": item['xmlid']} # Include xmlid for logging
                all_resolved = True
                for key, ref_id in item['ref_ids'].items():
                    uuid_val = self.id2uuid_map.get(ref_id)
                    if uuid_val is None:
                        _log.error(f"Deferred lookup failed! XML ID '{ref_id}' (key: {key}) still not found for crossEntry xmlid={item['xmlid']}")
                        all_resolved = False
                        break # Cannot proceed if any ID is missing
                    resolved_fields[key] = uuid_val

                if all_resolved:
                    # Call handle_crossEntry again, passing the resolved fields
                    self.handle_crossEntry(None, deferred_call=True, resolved_fields=resolved_fields)
                else:
                    _log.error(f"Skipping deferred crossEntry xmlid={item['xmlid']} due to unresolved references.")

            else:
                _log.warning(f"Unknown deferred item type: {item['type']}")

        _log.info("Deferred processing complete.")


if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="Import PortfolioPerformance XML file to Sqlite DB")
    argp.add_argument("xml_file", help="input XML file")
    argp.add_argument("db_file", help="output DB file")
    argp.add_argument("--debug", action="store_true", help="enable debug logging")
    argp.add_argument("--dry-run", action="store_true", help="don't commit changes to DB")
    argp.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = argp.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    dbhelper.init(args.db_file)

    with open(args.xml_file, "rb") as f:
        conv = PortfolioPerformanceXML2DB(f)
        conv.iterparse()

    if not args.dry_run:
        dbhelper.commit()
