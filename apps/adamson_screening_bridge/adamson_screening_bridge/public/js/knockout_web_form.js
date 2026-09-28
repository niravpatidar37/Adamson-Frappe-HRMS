// Shows only the knockout questions the chosen opening asks, worded with its
// actual requirement. Installed into hrms's job-application web form by
// knockout.ensure_web_form on every migrate; edit this file, not the form.
(() => {
	const QUESTIONS = {
		custom_ko_shift_ok: (v) => `Can you work this shift: ${v}?`,
		custom_ko_site_ok: (v) => `Can you travel to work at ${v}?`,
		custom_ko_certification_ok: (v) => `Do you hold this certification: ${v}?`,
		custom_ko_right_to_work_ok: () => "Are you legally authorized to work in this country?",
		custom_ko_start_by_ok: (v) => `Can you start on or before ${frappe.datetime.str_to_user(v)}?`,
	};

	const show = (opening) => {
		Object.keys(QUESTIONS).forEach((f) => {
			frappe.web_form.set_df_property(f, "hidden", 1);
			frappe.web_form.set_df_property(f, "reqd", 0);
		});
		if (!opening) return;
		frappe.call({
			method: "adamson_screening_bridge.knockout.get_knockout_questions",
			args: { job_opening: opening },
			callback: ({ message }) => {
				Object.entries(message || {}).forEach(([field, value]) => {
					frappe.web_form.set_df_property(field, "label", QUESTIONS[field](value));
					frappe.web_form.set_df_property(field, "hidden", 0);
					frappe.web_form.set_df_property(field, "reqd", 1);
				});
			},
		});
	};

	frappe.web_form.on("job_title", (field, value) => show(value));
	show(frappe.web_form.get_value("job_title"));
})();
