--
-- PostgreSQL database dump
--

\restrict YXenM1oCf40b1lpkeUogZkUJNa2bXd2iUBDlsLxscbVKNMtcTBpCxRwXkBf7QCY

-- Dumped from database version 16.15 (Debian 16.15-1.pgdg13+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_measurements; Type: TABLE; Schema: public; Owner: qsr_app
--

CREATE TABLE public.activity_measurements (
    id bigint NOT NULL,
    processing_run_id bigint NOT NULL,
    video_second integer NOT NULL,
    sample_count integer NOT NULL,
    mean_foreground_pixels double precision NOT NULL,
    mean_foreground_percent double precision NOT NULL,
    mean_large_foreground_blobs double precision NOT NULL,
    measurement_type text DEFAULT 'foreground_activity_proxy'::text NOT NULL,
    CONSTRAINT activity_measurements_mean_foreground_percent_check CHECK (((mean_foreground_percent >= (0)::double precision) AND (mean_foreground_percent <= (100)::double precision))),
    CONSTRAINT activity_measurements_mean_foreground_pixels_check CHECK ((mean_foreground_pixels >= (0)::double precision)),
    CONSTRAINT activity_measurements_mean_large_foreground_blobs_check CHECK ((mean_large_foreground_blobs >= (0)::double precision)),
    CONSTRAINT activity_measurements_sample_count_check CHECK ((sample_count > 0)),
    CONSTRAINT activity_measurements_video_second_check CHECK ((video_second >= 0))
);


ALTER TABLE public.activity_measurements OWNER TO qsr_app;

--
-- Name: activity_measurements_id_seq; Type: SEQUENCE; Schema: public; Owner: qsr_app
--

ALTER TABLE public.activity_measurements ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.activity_measurements_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: processing_runs; Type: TABLE; Schema: public; Owner: qsr_app
--

CREATE TABLE public.processing_runs (
    id bigint NOT NULL,
    video_filename text NOT NULL,
    measurement_method text NOT NULL,
    region_type text NOT NULL,
    video_width integer NOT NULL,
    video_height integer NOT NULL,
    video_fps double precision NOT NULL,
    video_duration_seconds double precision NOT NULL,
    region_pixels integer NOT NULL,
    warmup_frames_skipped integer DEFAULT 0 NOT NULL,
    status text DEFAULT 'completed'::text NOT NULL,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    notes text,
    CONSTRAINT processing_runs_region_pixels_check CHECK ((region_pixels > 0)),
    CONSTRAINT processing_runs_status_check CHECK ((status = ANY (ARRAY['completed'::text, 'failed'::text]))),
    CONSTRAINT processing_runs_video_duration_seconds_check CHECK ((video_duration_seconds >= (0)::double precision)),
    CONSTRAINT processing_runs_video_fps_check CHECK ((video_fps > (0)::double precision)),
    CONSTRAINT processing_runs_video_height_check CHECK ((video_height > 0)),
    CONSTRAINT processing_runs_video_width_check CHECK ((video_width > 0)),
    CONSTRAINT processing_runs_warmup_frames_skipped_check CHECK ((warmup_frames_skipped >= 0))
);


ALTER TABLE public.processing_runs OWNER TO qsr_app;

--
-- Name: processing_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: qsr_app
--

ALTER TABLE public.processing_runs ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.processing_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: activity_measurements; Type: TABLE DATA; Schema: public; Owner: qsr_app
--

COPY public.activity_measurements (id, processing_run_id, video_second, sample_count, mean_foreground_pixels, mean_foreground_percent, mean_large_foreground_blobs, measurement_type) FROM stdin;
1	1	2	1	48083	12.0634	15	foreground_activity_proxy
2	1	3	1	37916	9.5126	9	foreground_activity_proxy
3	1	4	1	77944	19.5551	12	foreground_activity_proxy
4	1	5	1	137714	34.5506	12	foreground_activity_proxy
5	1	6	1	109536	27.4811	17	foreground_activity_proxy
6	1	7	1	44649	11.2018	16	foreground_activity_proxy
7	1	8	1	39037	9.7939	18	foreground_activity_proxy
8	1	9	1	22879	5.74	11	foreground_activity_proxy
9	1	10	1	19318	4.8466	6	foreground_activity_proxy
10	2	2	1	48083	12.0634	15	foreground_activity_proxy
11	2	3	1	37916	9.5126	9	foreground_activity_proxy
12	2	4	1	77944	19.5551	12	foreground_activity_proxy
13	2	5	1	137714	34.5506	12	foreground_activity_proxy
14	2	6	1	109536	27.4811	17	foreground_activity_proxy
15	2	7	1	44649	11.2018	16	foreground_activity_proxy
16	2	8	1	39037	9.7939	18	foreground_activity_proxy
17	2	9	1	22879	5.74	11	foreground_activity_proxy
18	2	10	1	19318	4.8466	6	foreground_activity_proxy
19	3	2	1	11002	37.1614	3	foreground_activity_proxy
20	3	3	1	148	0.4999	0	foreground_activity_proxy
21	3	4	1	696	2.3509	0	foreground_activity_proxy
22	3	5	1	94	0.3175	0	foreground_activity_proxy
23	3	6	1	0	0	0	foreground_activity_proxy
24	3	7	1	210	0.7093	0	foreground_activity_proxy
25	3	8	1	446	1.5065	0	foreground_activity_proxy
26	3	9	1	1271	4.293	0	foreground_activity_proxy
27	3	10	1	173	0.5843	0	foreground_activity_proxy
28	3	11	1	1164	3.9316	1	foreground_activity_proxy
29	3	12	1	944	3.1885	1	foreground_activity_proxy
30	3	13	1	509	1.7192	0	foreground_activity_proxy
31	3	14	1	115	0.3884	0	foreground_activity_proxy
32	3	15	1	0	0	0	foreground_activity_proxy
33	3	16	1	0	0	0	foreground_activity_proxy
34	3	17	1	0	0	0	foreground_activity_proxy
35	3	18	1	73	0.2466	0	foreground_activity_proxy
36	3	19	1	126	0.4256	0	foreground_activity_proxy
37	3	20	1	6266	21.1646	2	foreground_activity_proxy
38	3	21	1	6764	22.8467	2	foreground_activity_proxy
39	3	22	1	9	0.0304	0	foreground_activity_proxy
\.


--
-- Data for Name: processing_runs; Type: TABLE DATA; Schema: public; Owner: qsr_app
--

COPY public.processing_runs (id, video_filename, measurement_method, region_type, video_width, video_height, video_fps, video_duration_seconds, region_pixels, warmup_frames_skipped, status, started_at, notes) FROM stdin;
1	counter.mp4	OpenCV MOG2 background subtraction	service_activity_region	2560	1440	29.97002997002997	10.276933333333334	398586	60	completed	2026-10-23 09:46:09.078585+00	Foreground activity proxy, not a verified customer count. Queue region not independently validated.
2	counter.mp4	OpenCV MOG2 background subtraction	service_activity_region	2560	1440	29.97002997002997	10.276933333333334	398586	60	completed	2026-10-23 09:56:12.378014+00	Foreground activity proxy, not a verified customer count. Queue region not independently validated.
3	normal_queue.mp4	OpenCV MOG2 background subtraction	service_activity_region	240	426	29.97002997002997	22.489133333333335	29606	60	completed	2026-10-23 09:56:15.514078+00	Foreground activity proxy, not a verified customer count. Queue region not independently validated.
\.


--
-- Name: activity_measurements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: qsr_app
--

SELECT pg_catalog.setval('public.activity_measurements_id_seq', 39, true);


--
-- Name: processing_runs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: qsr_app
--

SELECT pg_catalog.setval('public.processing_runs_id_seq', 3, true);


--
-- Name: activity_measurements activity_measurements_pkey; Type: CONSTRAINT; Schema: public; Owner: qsr_app
--

ALTER TABLE ONLY public.activity_measurements
    ADD CONSTRAINT activity_measurements_pkey PRIMARY KEY (id);


--
-- Name: activity_measurements activity_measurements_processing_run_id_video_second_key; Type: CONSTRAINT; Schema: public; Owner: qsr_app
--

ALTER TABLE ONLY public.activity_measurements
    ADD CONSTRAINT activity_measurements_processing_run_id_video_second_key UNIQUE (processing_run_id, video_second);


--
-- Name: processing_runs processing_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: qsr_app
--

ALTER TABLE ONLY public.processing_runs
    ADD CONSTRAINT processing_runs_pkey PRIMARY KEY (id);


--
-- Name: idx_activity_measurements_run_second; Type: INDEX; Schema: public; Owner: qsr_app
--

CREATE INDEX idx_activity_measurements_run_second ON public.activity_measurements USING btree (processing_run_id, video_second);


--
-- Name: idx_processing_runs_video; Type: INDEX; Schema: public; Owner: qsr_app
--

CREATE INDEX idx_processing_runs_video ON public.processing_runs USING btree (video_filename);


--
-- Name: activity_measurements activity_measurements_processing_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: qsr_app
--

ALTER TABLE ONLY public.activity_measurements
    ADD CONSTRAINT activity_measurements_processing_run_id_fkey FOREIGN KEY (processing_run_id) REFERENCES public.processing_runs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict YXenM1oCf40b1lpkeUogZkUJNa2bXd2iUBDlsLxscbVKNMtcTBpCxRwXkBf7QCY

