// Recruiter list: Eligible first, then Unanswered, then Declared Ineligible,
// oldest application first within each (see knockout_rules.sort_key).
// Extends hrms's list settings instead of replacing them.
frappe.listview_settings["Job Applicant"] = frappe.listview_settings["Job Applicant"] || {};
(() => {
	const settings = frappe.listview_settings["Job Applicant"];
	const hrms_onload = settings.onload;
	const hrms_indicator = settings.get_indicator;

	settings.onload = function (listview) {
		if (hrms_onload) hrms_onload(listview);
		listview.sort_selector.set_value("custom_knockout_sort_key", "asc");
	};

	// Declared Ineligible is flagged, not hidden: a recruiter confirms each one.
	settings.get_indicator = function (doc) {
		if (doc.custom_knockout_result === "Declared Ineligible") {
			return [__("Declared Ineligible"), "orange", "custom_knockout_result,=,Declared Ineligible"];
		}
		return hrms_indicator ? hrms_indicator(doc) : null;
	};
	settings.add_fields = [...(settings.add_fields || []), "custom_knockout_result"];
})();
