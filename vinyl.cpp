#include "pch.h"
#include <opencv2\opencv.hpp>
#include <cxxopts.hpp>
#include "stopwatch.h"

/**
 * Takes a single frame and returns the dominant color.
 *
 * @param frame
 * @param crop optional Crop
 * @param scale optional downscaling
 * @param preview whether a preview should be displayed
 * @return a Vec3b with the dominant color in RGB
 */
cv::Vec3b get_dominant_color(cv::Mat frame, cv::Rect2i crop = cv::Rect2i(), cv::Size scale = cv::Size(), bool preview = false) {
	// optional cropping (to remove black bars)
	if (crop != cv::Rect2i()) frame = frame(crop);
	// optional donwscaling (increases performance significantly)
	if (scale != cv::Size()) cv::resize(frame, frame, scale, (0.0), (0.0), cv::INTER_AREA);

	// generate preview
	cv::Mat preview_frame;
	if (preview) {
		preview_frame = cv::Mat(cv::Size(frame.size().width, frame.size().height + 20), frame.type());
		frame.copyTo(preview_frame(cv::Rect2i(0, 0, frame.size().width, frame.size().height)));
	}

	// k-means
	frame.convertTo(frame, CV_32F);
	frame = frame.reshape(1, frame.total());
	cv::Mat labels, centers;
	cv::kmeans(frame, 1, labels, cv::TermCriteria(cv::TermCriteria::EPS, 10, 1.0), 3, cv::KMEANS_PP_CENTERS, centers);

	if (preview) {
		// dominant color in a box
		cv::rectangle(preview_frame, cv::Rect2i(0, preview_frame.size().height - 20, preview_frame.size().width, 20), centers.at<cv::Vec3f>(0, 0), cv::FILLED);
		cv::rectangle(preview_frame, cv::Rect2i(0, preview_frame.size().height - 20, preview_frame.size().width, 20), cv::Scalar(32, 32, 192));

		// print RGB as text on screen
		std::stringstream text;
		text << "R" << std::setfill('0') << std::setw(3) << (int)centers.at<cv::Vec3f>(0, 0)[2]
			<< " G" << std::setfill('0') << std::setw(3) << (int)centers.at<cv::Vec3f>(0, 0)[1]
			<< " B" << std::setfill('0') << std::setw(3) << (int)centers.at<cv::Vec3f>(0, 0)[0];
		cv::putText(preview_frame, text.str(), cv::Point2i(5, preview_frame.size().height - 5), cv::FONT_HERSHEY_PLAIN, 1, cv::Scalar(255, 255, 255));

		// show the preview image
		cv::imshow("preview", preview_frame);
		cv::waitKey(1);
	}

	// return dominant color as RGB
	return cv::Vec3b(centers.at<cv::Vec3f>(0, 0)[2], centers.at<cv::Vec3f>(0, 0)[1], centers.at<cv::Vec3f>(0, 0)[0]);
}

/**
 * Takes a path to a video and returns a list of all dominant colors
 *
 * @param path
 * @param crop Optional Crop
 * @param scale Optional downscaling
 * @param preview Whether a preview should be displayed
 * @return A list with colors as Vec3b in RGB
 */
std::list<cv::Vec3b> get_colors(std::string path, std::vector<uint> crop, std::vector<uint> scale, bool preview) {
	// open video file
	cv::VideoCapture cap(path);
	if (!cap.isOpened()) {
		std::cout << "Cannot open " << path << std::endl;
		throw new std::runtime_error("Cannot open " + path);
	}

	size_t total_frames = cap.get(cv::CAP_PROP_FRAME_COUNT);
	uint frame_width = cap.get(cv::CAP_PROP_FRAME_WIDTH);
	uint frame_height = cap.get(cv::CAP_PROP_FRAME_HEIGHT);

	// calculate crop rectangle
	cv::Rect2i crop_area = cv::Rect2i();
	if (crop.size() == 2 && crop[0] > 0 && crop[1] > 0) {
		if (((float)frame_width / frame_height) < ((float)crop[0] / crop[1])) {
			crop_area = cv::Rect2i(0, (frame_height - frame_width * ((float)crop[1] / crop[0])) / 2, frame_width, frame_width * ((float)crop[1] / crop[0]));
		} else if (((float)frame_width / frame_height) > ((float)crop[0] / crop[1])) {
			crop_area = cv::Rect2i((frame_width - frame_height * ((float)crop[0] / crop[1])) / 2, 0, frame_height * ((float)crop[0] / crop[1]), frame_height);
		}
	} else if (crop.size() == 4 && crop[2] > 0 && crop[3] > 0 && (crop[0] + crop[2] <= frame_width) && (crop[1] + crop[3] <= frame_height)) {
		crop_area = cv::Rect2i(crop[0], crop[1], crop[2], crop[3]);
	}
	
	// calculate downscaling
	cv::Size2i scale_size = cv::Size2i();
	if (scale.size() == 1 && scale[0] > 0) {
		if (crop_area == cv::Rect2i()) {
			scale_size = cv::Size2i(frame_width / scale[0], frame_height / scale[0]);
		} else {
			scale_size = cv::Size2i(crop_area.width / scale[0], crop_area.height / scale[0]);
		}
	}
	else if (scale.size() == 2 && scale[0] > 0 && scale[1] > 0) {
		scale_size = cv::Size2i(scale[0], scale[1]);
	}

	// stopwatch to calculate FPS and ETA
	Stopwatch stopwatch = Stopwatch();

	// list of all dominant colors
	std::list<cv::Vec3b> colors;

	// frame
	cv::Mat frame;

	stopwatch.Start();

	while (true) {
		// get the next frame
		cap >> frame;

		if (frame.empty()) {
			if (cap.get(cv::CAP_PROP_POS_FRAMES) < total_frames) {
				// This is weird. Internet sais empty frame means EOF, but I had empty strings in the middle of videos before, especially mkv with webm
				continue;
			} else {
				// EOF
				return colors;
			}
		}

		// append the dominant color to the list
		colors.insert(colors.end(), get_dominant_color(frame, crop_area, scale_size, preview));
		
		// print current stat and ETA to std::cout
		stopwatch.Lap();
		float wma = stopwatch.weightedMovingAverage();
		int eta = (total_frames - cap.get(cv::CAP_PROP_POS_FRAMES)) * wma;
		std::cout << "Frame " << (int)cap.get(cv::CAP_PROP_POS_FRAMES) << "/" << total_frames << " @ " << std::setprecision(4) << (1/wma) << " FPS (" << (100.0f * cap.get(cv::CAP_PROP_POS_FRAMES) / total_frames) << "%) ETA " << (int)(eta/60) << " minutes " << (int)(eta%60) << " seconds" << std::endl;
	}
}

#define PI 3.141592653589793238463f
inline float RTHEHTA(float theta, float radius_base) { return radius_base + theta / (2 * PI); }
inline float DELTATHETA(float theta, float radius_base, float b) { return b / RTHEHTA(theta, radius_base); }

/**
 * Takes a list of colors and generates a spiral in svg
 *
 * @param colors
 * @param radius_base Eadius of the inner circle
 * @param arc Length of each individual colored arc segment
 * @return A string containing the svg document
 */
std::string spiral(std::list<cv::Vec3b> colors, float radius_base, float arc) {
	// theta is the current angle in radians
	float theta = 0.0f;

	std::stringstream spiral;
	std::stringstream arc_segments;

	for (cv::Vec3b c : colors) {
		float dtheta = DELTATHETA(theta, radius_base, arc * 1.1f);
		float rtheta = RTHEHTA(theta, radius_base);

		// svg path for a single arc segment
		arc_segments << "  <path d=\"M " << (std::sin(theta) * RTHEHTA(theta, radius_base)) << " " << (std::cos(theta) * RTHEHTA(theta, radius_base))
			<< " A " << rtheta << " " << rtheta << " 0 0 0 " << std::sin(theta + dtheta) * RTHEHTA(theta + dtheta, radius_base) << " " << std::cos(theta + dtheta) * RTHEHTA(theta + dtheta, radius_base)
			<< "\" fill=\"none\" stroke-width=\"1.1\" stroke=\"#"
			<< std::hex << std::setfill('0') << std::setw(2) << (int)c[0] << std::setfill('0') << std::setw(2) << (int)c[1] << std::setfill('0') << std::setw(2) << (int)c[2]
			<< "\"/>" << std::endl;

		theta += DELTATHETA(theta, radius_base, arc);
	}

	float r_max = std::ceil(RTHEHTA(theta + 2 * PI, radius_base));
	spiral << "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"" << -r_max << " " << -r_max << " " << 2 * r_max << " " << 2 * r_max << "\">" << std::endl;
	spiral << arc_segments.str();
	spiral << "</svg>" << std::endl;

	return spiral.str();
}

int main(int argc, char** argv)
{
#ifdef _DEBUG
	std::cout << "Debug build" << std::endl;
#endif
	// argument parsing
	bool preview;

	float radius;
	float arc;

	std::vector<uint> crop;
	std::vector<uint> scale;

	std::vector<std::string> unmatched;

	cxxopts::Options opt_config("Vinyl", "Create vinyl images from video files");
	opt_config.add_options()
		("p,preview", "show preview")
		("r,radius", "Inner radius", cxxopts::value<float>()->default_value("10.0f"))
		("arc", "Arc segment length", cxxopts::value<float>()->default_value("1.0f"))
		("crop", "crop x,y,width,height or ratioX,ratioY (applied before scale)", cxxopts::value<std::vector<uint>>())
		("scale", "downscaling width,height or factor", cxxopts::value<std::vector<uint>>()->default_value("4"))
		("h,help", "Print help")
		;

	cxxopts::ParseResult opt_result;
	try {
		opt_result = opt_config.parse(argc, argv);
	} catch (cxxopts::OptionException e) {
		std::cout << e.what() << std::endl;
		std::cout << "Use --help for more information" << std::endl;
		exit(0);
	}

	if (opt_result.count("help")) {
		std::cout << opt_config.help() << std::endl;
		exit(0);
	}

	unmatched = opt_result.unmatched();
	if (unmatched.size() == 0) {
		std::cout << "No input file(s) provided." << std::endl;
		exit(0);
	}

	preview = (bool)opt_result["preview"].count();

	radius = opt_result["radius"].as<float>();
	if (radius <= 0) {
		std::cout << "radius must be greater than zero" << std::endl;
		exit(0);
	}

	arc = opt_result["arc"].as<float>();
	if (arc <= 0) {
		std::cout << "arc must be greater than zero" << std::endl;
		exit(0);
	}

	if (opt_result["crop"].count()) {
		crop = opt_result["crop"].as<std::vector<uint>>();
		if ((crop.size() != 2 && crop.size() != 4)) {
			std::cout << "crop invalid" << std::endl;
			exit(0);
		}
	}

	if (opt_result["scale"].count()) {
		scale = opt_result["scale"].as<std::vector<uint>>();
		if ((scale.size() != 1 && scale.size() != 2)) {
			std::cout << "scale invalid" << std::endl;
			exit(0);
		}
	}

#ifdef _DEBUG
	std::cout << "preview " << (preview ? "enabled" : "disabled") << std::endl;
	std::cout << "radius= " << radius << std::endl;
	std::cout << "arc= " << arc << std::endl;

	std::cout << "crop=[";
	for (std::vector<uint>::const_iterator i = crop.cbegin(); i != crop.cend(); ++i) std::cout << *i << (std::next(i) == crop.cend() ? "" : ", ");
	std::cout << "]" << std::endl;

	std::cout << "scale=[";
	for (std::vector<uint>::const_iterator i = scale.cbegin(); i != scale.cend(); ++i) std::cout << *i << (std::next(i) == scale.cend() ? "" : ", ");
	std::cout << "]" << std::endl;
#endif // _DEBUG

	// for each submitted video
	for (std::string s : unmatched)	{
		try {
			// get the list of dominant colors
			std::list<cv::Vec3b> colors = get_colors(s, crop, scale, preview);
			colors.reverse();

			// generate the svg string
			std::string svg = spiral(colors, radius, arc);

			// write the svg to a file
			std::ofstream fp(s.substr(0, s.find_last_of('.')) + ".svg");
			fp << svg;
			fp.close();

		} catch (std::exception e) {
			std::cout << e.what() << std::endl;
		}
	}

}
