import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "cbr_dailyinfo");
const DYN = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetCursDynamicResponse xmlns="http://web.cbr.ru/"><GetCursDynamicResult><diffgr:diffgram xmlns:msdata="urn:schemas-microsoft-com:xml-msdata" xmlns:diffgr="urn:schemas-microsoft-com:xml-diffgram-v1"><ValuteData xmlns=""><ValuteCursDynamic diffgr:id="ValuteCursDynamic1" msdata:rowOrder="0"><CursDate>2026-09-25T00:00:00+03:00</CursDate><Vcode>R01235</Vcode><Vnom>1</Vnom><Vcurs>84.9057</Vcurs><VunitRate>84.9057</VunitRate></ValuteCursDynamic></ValuteData></diffgr:diffgram></GetCursDynamicResult></GetCursDynamicResponse></soap:Body></soap:Envelope>';

test("cbr SOAP envelope, SOAPAction and a one-row DataSet (wire)", async () => {
  const { call, log } = await connect(SPEC, () => ({ body: DYN, type: "text/xml; charset=utf-8" }));
  const pts = (await call("get_series", { series_id: "R01235", start: "2026-09-25", end: "2026-09-30" })).structuredContent.points;
  assert.deepEqual(pts.map((p) => [p.time, p.value]), [["2026-09-25T00:00:00+03:00", 84.9057]]);
  assert.equal(log[0].url.toString(), "https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx");
  assert.equal(log[0].init.headers.SOAPAction, '"http://web.cbr.ru/GetCursDynamic"');
  assert.match(log[0].init.body, /<GetCursDynamic xmlns="http:\/\/web.cbr.ru\/"><FromDate>2026-09-25<\/FromDate><ToDate>2026-09-30<\/ToDate><ValutaCode>R01235<\/ValutaCode>/);
});
