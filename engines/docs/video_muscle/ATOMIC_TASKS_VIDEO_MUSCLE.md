task_id	lane	description	acceptance_criteria
T_VID_01	Wrapper	Create `engines/muscles/video_timeline/mcp_wrapper.py`.	Expose `get_project`, `list_sequences` as `video.timeline.read`.
T_VID_02	Wrapper	Add mutators to Timeline Wrapper.	Expose `trim_clip`, `split_clip`, `move_clip` as `video.timeline.write`.
T_VID_03	Wrapper	Create `engines/muscles/video_render/mcp_wrapper.py`.	Expose `render_scope` (submit job) and `status_scope`.
T_VID_04	GateChain	Implement Permissions in Wrapper `video.timeline.admin`.	Ensure `delete_project` checks `ctx.policy.check_firearms()`.
T_VID_05	GateChain	Implement Permissions in Wrapper `video.render.submit`.	Ensure `submit_render` checks `ctx.policy.check_firearms("production_budget")`.
T_VID_06	Registration	Register Video Scopes in Inventory (Standard).	Use dynamic loader or config; NO hardcoded `inventory.py` edits.
T_VID_07	QA	Verify MCP "Render & Wait" Flow.	Agent can: Read Timeline -> Submit Render -> Poll Status -> Get URL.
