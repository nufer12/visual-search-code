<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'response.php';
require_once 'image.php';
require_once 'search.php';
require_once 'auth.php';

set_time_limit(0);

class UploadService
{

    const prometheusAlias = [
        'artist' => ['artist', 'identity artist', 'title variants', 'artist information', 'caption'],
        'title' => ['title', 'subtitle', 'descriptive title'],
        'date' => ['date'],
        'genre' => ['genre'],
        'epoch' => ['epoch'],
        'measurements' => ['size', 'height', 'sheetsize', 'length', 'measure'],
        'material' => ['material'],
        'technique' => ['technique'],
        'institution' => ['institution', 'keyword location'],
        'provenienz' => ['provenienz'],
        'iconclass' => ['iconclass'],
        'status' => [],
    ];

    public static function prometheusParseLine(string $line): array
    {
        $data = explode(':', $line, 2);
        $data[0] = strtolower(trim($data[0]));
        $data[1] = trim($data[1]);
        return $data;
    }

    public static function prometheusDescriptionToArray($filename): array
    {
        $prometheusDataRaw = file_get_contents($filename);
        // Replace double new lines which are followed by a single-line string containing a : with a line break
        $prometheusDataRaw = preg_replace('/\\n\s*\\n([^\n]+:)/', '[[BREAK]]$1', $prometheusDataRaw);
        $prometheusDataRaw = explode('[[BREAK]]', $prometheusDataRaw);
        $prometheusData = array_map(array("UploadService", "prometheusParseLine"), $prometheusDataRaw);
        $prometheusData = array_combine(array_column($prometheusData, 0), array_column($prometheusData, 1));

        $data = [];
        foreach (Image::updateable_values as $key => $attr) {
            foreach (UploadService::prometheusAlias[$attr] as $attr2 => $alias) {
                if (array_key_exists($alias, $prometheusData)) {
                    $data[$attr] = $prometheusData[$alias];
                    break;
                }
            }
        }
        return $data;
    }

    public static function processFile($collection_id): array
    {

	echo '--------------0-------------';

        if (empty($_FILES)) {
            ResponseService::throw(APIError::E_INPUT_UPLOAD_EMPTY, $_FILES);
        }
        if ($_FILES["file"]["error"] == 1) {
            ResponseService::throw(APIError::E_INPUT_UPLOAD_TOO_LARGE);
        }

        // get pathes
        $base_folder = _DATA_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . 'uploads';
        $file_ext = pathinfo($_FILES['file']['name'], PATHINFO_EXTENSION);
        $upload_path = $base_folder . DIRECTORY_SEPARATOR . 'user_' . AuthService::$id . '_' . time() . '_' . rand(0, 1000) . '.' . $file_ext;

        /*

        Image

         */
        $allowed_image_types = [1, 2, 3];
        $allowed_image_mime = ["image/gif", "image/jpg", "image/jpeg", "image/bmp", "image/png", "image/pjpeg", "image/x-png", "application/octet-stream"];

	echo '--------------1-------------';

        $file_type = exif_imagetype($_FILES['file']['tmp_name']);
        // jap, is an image
        if (in_array($file_type, $allowed_image_types) && in_array(strtolower($_FILES["file"]["type"]), $allowed_image_mime)) {

	    echo '--------------2-------------';

            $file_real_name = pathinfo($_FILES['file']['name'], PATHINFO_FILENAME);
            move_uploaded_file($_FILES['file']['tmp_name'], $upload_path);
            $image_id = Image::new ($collection_id, $upload_path, $file_real_name);
            return ["image_id" => $image_id];
        }

        /*

        prometheus file

         */
        if ($file_ext == 'zip') {
	    echo '1';
            move_uploaded_file($_FILES['file']['tmp_name'], $upload_path);
	    echo '2';
            $counter_images = 0;
            $counter_metas = 0;
            $meta_info = [];
            $zip_data = new ZipArchive;
            // unzip
	    echo '3';
            if ($zip_data->open($upload_path)) {
                for ($i = 0; $i < $zip_data->numFiles; $i++) { // loop files
                    $zfullname = $zip_data->getNameIndex($i);
                    $zip_data->extractTo($base_folder, $zfullname);
                    $zextension = pathinfo($zfullname, PATHINFO_EXTENSION);
                    $zfilename = pathinfo($zfullname, PATHINFO_FILENAME);
                    // text or image?
                    if ($zextension == 'txt') {
                        $meta_info[$zfilename] = UploadService::prometheusDescriptionToArray($base_folder . DIRECTORY_SEPARATOR . $zfullname);
                    } else {
                        $type = exif_imagetype($base_folder . DIRECTORY_SEPARATOR . $zfullname);
                        if (in_array($type, $allowed_image_types)) { // image
                            Image::new ($collection_id, $base_folder . DIRECTORY_SEPARATOR . $zfullname, $zfilename);
                            $counter_images += 1;
                        } else {
                            unlink($base_folder . DIRECTORY_SEPARATOR . $zfullname);
                        }
                    }
                }
                // update images with collected meta information
                foreach ($meta_info as $zfilename => $values) {
                    $c = Image::updateByUserCollectionAndName(AuthService::$id, $collection_id, $zfilename, $values);
                    if ($c !== null) {
                        $counter_metas += 1;
                    }
                }
            } else {
                ResponseService::throw(APIError::E_SERVER_UPLOAD_OPEN_ZIP);
            }
            $zip_data->close();
            unlink($zip_target);
            return ['images' => $counter_images, 'meta' => $counter_metas];
        }

        /*

        CSV

         */

        if ($file_ext == 'csv') {
            move_uploaded_file($_FILES['file']['tmp_name'], $upload_path);
            $csv = array_map('str_getcsv', file($upload_path));
            $csv[0][0] = "filename";
            $counter = 0;
            #$currentUserID = CurrentUserService::get()->id;
            $currentUserID = AuthService::$id;  # NON
            for ($i = 1; $i < count($csv); $i++) {
                $toInsert = array_combine($csv[0], $csv[$i]);
                // TD: add meta counter
                $c = Image::updateByUserCollectionAndName($currentUserID, $collection_id, $csv[$i][0], $toInsert);
                if ($c !== null) {
                    $counter += 1;
                }
            }
            return ['meta' => $counter];
        }

        /*

        JSON (as search result)
        // TD: check if storage conventions are still valid

         */

        if ($file_ext == 'json') {

            $search_counter = 0;
            $retrieval_counter = 0;

            // assume to have new searches to import
            move_uploaded_file($_FILES['file']['tmp_name'], $upload_path);
            $data = file_get_contents($upload_path);
            // $data = stripslashes($data);
            $data = str_replace('NaN', 0, $data);
            $data = json_decode($data, true);
            // TD: please, another storage convention :/
            $index_id = $data["index_id"];

            foreach ($data["data"] as $key => $value) {
                $query_img = $value["img_id"];
                $query_bbox = $value["bbs"];
                $search_id = Search::new ($index_id, ["image_id" => $query_img, "base" => null, "search_boxes" => $query_bbox, "name" => "Imported, " . time(), "params" => ""], false);
                Search::update($search_id, ['total_hits' => count($value["retrievals"])]);
                $search_counter += 1;
                foreach ($value["retrievals"] as $key2 => $retrieval) {
                    $retrieval_img = $retrieval[0];
                    $retrieval_bbox = $retrieval[1];
                    $retrieval_score = $retrieval[3];
                    $retrieval_scores = $retrieval[2];
                    $retrieval_tsne = $retrieval[5];
                    // TD: make only one insert call
                    SearchResult::new ($retrieval_img, $search_id, $retrieval_score, $retrieval_bbox, $retrieval_scores, $retrieval_tsne);
                    $retrieval_counter += 1;
                }
            }
            rename($upload_path, _DATA_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . 'index_' . $index_id . DIRECTORY_SEPARATOR . 'retrieval' . DIRECTORY_SEPARATOR . 'imported_user_' . AuthService::$id . '_' . time() . '.json');
            return ["searches" => $search_counter, "retrievals" => $retrieval_counter];
        }

        ResponseService::throw(APIError::E_INPUT_UPLOAD_UNKNOWN);
    }

}
