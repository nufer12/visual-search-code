<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'response.php';
require_once 'dbservice.php';

require_once 'util.php';
require_once 'auth.php';
require_once 'collection.php';

class Image extends DatabaseInterface implements JsonSerializable
{
    public $id;
    public $collection_id;
    public $filename;
    public $upload_date;
    public $upload_user;
    public $upload_username;
    public $status;
    public $orig_filename;
    public $artist;
    public $title;
    public $date;
    public $genre;
    public $epoch;
    public $measurements;
    public $material;
    public $technique;
    public $institution;
    public $provenance;
    public $iconclass;
    public $year;

    private $short = false;

    const updateable_values = ['artist', 'title', 'date', 'genre', 'epoch', 'measurements', 'material', 'technique', 'institution', 'provenance', 'iconclass', 'year'];
    const table_name = 'vis_images';

    public static function getDBValuesForNew($params): array
    {
        return [
            'id' => null,
            'collection_id' => $params[0],
            'filename' => $params[1] . '.' . $params[2],
            'upload_date' => date('Y-m-d H:i:s'),
            'upload_user' => AuthService::$id,
            'status' => 0,
            'orig_filename' => $params[3],
        ];
    }

    public function jsonSerialize(): array
    {
        if ($this->short) {
            return [
                'id' => $this->id,
                'filename' => $this->filename,
            ];
        } else {
            return [
                'id' => $this->id,
                'collection_id' => $this->collection_id,
                'upload_date' => $this->upload_date,
                'upload_user' => $this->upload_user,
                'filename' => $this->filename,
                'upload_username' => User::getUserName($this->upload_user),
                'status' => $this->status,
                'orig_filename' => $this->orig_filename,
                'artist' => $this->artist,
                'title' => $this->title,
                'date' => $this->date,
                'genre' => $this->genre,
                'epoch' => $this->epoch,
                'measurements' => $this->measurements,
                'material' => $this->material,
                'technique' => $this->technique,
                'institution' => $this->institution,
                'provenance' => $this->provenance,
                'iconclass' => $this->iconclass,
                'year' => $this->year,
            ];
        }
    }
    public function __construct($short = false)
    {
        $this->short = $short;
    }
    

    public static function ofCollection(int $collection_id, $state = null, $short = true, $limits = [], $filter = '', $year_range = []): array
    {
        // deleted or not? or all?
        $state_cond = ($state === null) ? '' : ' AND `vis_images`.`status` = :state';
        // search keyword condition
        $filter_cond = ($filter == '') ? '' : ' AND MATCH(`' . implode('`, `', ['artist', 'title', 'date', 'genre', 'epoch', 'measurements', 'material', 'technique', 'institution', 'provenance', 'iconclass']) . '`) AGAINST (:matching IN BOOLEAN MODE)';
        // year condition
        $year_cond = (count($year_range) < 2) ? '' : ' AND `vis_images`.`year` >= :yearmin AND `vis_images`.`year` <= :yearmax';

        $bindings = [
            ":collectionid" => $collection_id,
        ];
        if ($state !== null) {
            $bindings[':state'] = $state;
        }
        if ($filter != '') {
            $bindings[':matching'] = $filter . '*';
        }
        if (count($year_range) == 2) {
            $bindings[':yearmin'] = $year_range[0];
            $bindings[':yearmax'] = $year_range[1];
        }

        return DBService::getData(
            'Image-ofCollection:' . $collection_id,
            "SELECT `vis_images`.* FROM `vis_images` WHERE `vis_images`.`collection_id` = :collectionid" . $state_cond . $filter_cond . $year_cond . " ORDER BY `vis_images`.`upload_date` DESC",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__, [$short]],
            $limits
        );
        // CACHE: cleared in
        // - Image::update
        // - Image::updateByUserCollectionAndName
        // - Image::remove
        // - Image::recover
        // - Image::new

    }

    /*

    Create new

     */

    public static function new (...$params): int {
        $collection_id = $params[0];
        $path_to_file = $params[1];
        $orig_name = $params[2];
        $extension = pathinfo($path_to_file, PATHINFO_EXTENSION);
        $image_id = parent::new ($collection_id, '', $extension, $orig_name);

        // well, that is a bit messy
        // parallel upload failes on getting the correct image id, thats why a random number is needed
        $new_file_name = 'img_' . $image_id . '_' . rand(0, 1000);
        Image::update($image_id, ['filename' => $new_file_name . '.' . $extension]);
        
        $folder_name = _DATA_ . 'images_' . $collection_id;
        // move to new folder
        rename($path_to_file, $folder_name . DIRECTORY_SEPARATOR . "images" . DIRECTORY_SEPARATOR . $new_file_name . '.' . $extension);
        // create thumbnail
        Image::createThumbnail(
            $folder_name . DIRECTORY_SEPARATOR . "images" . DIRECTORY_SEPARATOR . $new_file_name . '.' . $extension,
            _THUMBS_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . $new_file_name . '.jpg',
            300, 300
        );
        // modify collection
        Collection::addToImageCounter($collection_id, 1);
        Collection::markIndicesAsModified($collection_id);

        DBService::clearCache('Image-ofCollection:'.$collection_id);
        // CACHE: set in Image::ofCollection
        return $image_id;
    }

    public static function createThumbnail(string $filepath, string $thumbpath, int $thumbnail_width, int $thumbnail_height)
    {
        // function to create a thumbnail
        list($original_width, $original_height, $original_type) = getimagesize($filepath);
        if ($original_width > $original_height) {
            $new_width = $thumbnail_width;
            $new_height = intval($original_height * $new_width / $original_width);
        } else {
            $new_height = $thumbnail_height;
            $new_width = intval($original_width * $new_height / $original_height);
        }
        $imgt = "ImageJPEG";
        if ($original_type === 1) {
            $imgcreatefrom = "ImageCreateFromGIF";
        } else if ($original_type === 2) {
            $imgcreatefrom = "ImageCreateFromJPEG";
        } else if ($original_type === 3) {
            $imgcreatefrom = "ImageCreateFromPNG";
        } else {
            return false;
        }
        $old_image = $imgcreatefrom($filepath);
        $new_image = imagecreatetruecolor($new_width, $new_height);
        imagecopyresampled($new_image, $old_image, 0, 0, 0, 0, $new_width, $new_height, $original_width, $original_height);
        $imgt($new_image, $thumbpath);
        return file_exists($thumbpath);
    }

    /*

    Modify

     */

    public static function remove($image_id)
    {
        $img = Image::getByID($image_id);
        Image::update($image_id, array('status' => 9));
        // DBService::clearCache("Image-ofCollection:" . $img->collection_id);
        // CACHE: set in Image::ofCollection
        // cleared in Update call
        Collection::addToImageCounter($img->collection_id, -1);
        return true;
    }
    public static function recover($image_id)
    {
        $img = Image::getByID($image_id);
        Image::update($image_id, array('status' => 0));
        // DBService::clearCache("Image-ofCollection:" . $img->collection_id);
        // CACHE: set in Image::ofCollection
        // cleared in Update call
        Collection::addToImageCounter($img->collection_id, 1);
        return true;
    }

    public static function updateByUserCollectionAndName(int $user_id, int $collection_id, string $filename, $values): int
    {
        // try to get the year out of the date field
        if (isset($values['date'])) {
            $matches = [];
            $succ = preg_match('/(^|\s|\.)(\d{1,4})(\,|\;|\s|$)/', $values['date'], $matches);
            if ($succ) {
                $values['year'] = intval($matches[2]);
            }
        }

        $keys = array_keys($values);
        $update_statements = array_map(function ($key) {
            if (in_array($key, Image::updateable_values)) {
                return "`" . $key . "` = :" . $key;
            }
        }, $keys);

        try {
            #$statement = DBService::getPDO()->prepare("UPDATE `vis_images` SET " . implode(', ', $update_statements) . " WHERE `orig_filename` = :filename AND `collection_id` = :collectionid AND `upload_user` = :userid");
            $statement = DBService::getPDO()->prepare("UPDATE `vis_images` SET " . trim(join(', ', $update_statements), ', ') . " WHERE `orig_filename` = :filename AND `collection_id` = :collectionid AND `upload_user` = :userid");  # NON

            foreach ($values as $key => $value) {
                $statement->bindValue(':' . $key, $value);
            }
            $statement->bindValue(':collectionid', $collection_id);
            $statement->bindValue(':userid', $user_id);
            $statement->bindValue(':filename', $filename);
            $statement->execute();
            DBService::clearCache("Image-ofCollection:" . $collection_id);
            DBService::clearCache("Obj-Image");
            // CACHE: set in Image::ofCollection
            return $statement->rowCount();
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function update(int $id, array $values, $safe = false): int
    {
        // try to get the year out of the date field
        if (isset($values['date'])) {
            $matches = [];
            $succ = preg_match('/(^|\s|\.|\-)(\d{1,4})(\,|\;|\s|$)[^\d]*$/', $values['date'], $matches);
            if ($succ) {
                $values['year'] = intval($matches[2]);
            }
        }
        $image_info = Image::getByID($id);
        DBService::clearCache("Image-ofCollection:" . $image_info->collection_id);
        return parent::update($id, $values, $safe);
    }

    /*

    Serve Image file

     */

    public static function show(int $collection_id, string $image_name, $type = 'images')
    {
        if ($type == 'images') {
            $image_path = _DATA_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . 'images' . DIRECTORY_SEPARATOR . $image_name;
            if (file_exists($image_path)) {
                ResponseService::serveImage($image_path);
            }
        }
        // fallback
        $image_path = _THUMBS_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . $image_name;
        if (!file_exists($image_path)) {
            ResponseService::throw(APIError::E_NOTFOUND_FILE);
        } else {
            ResponseService::serveImage($image_path);
        }
    }

}
